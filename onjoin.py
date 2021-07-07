import json
import os
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info(event)
    logger.info("kres")

    data_base = boto3.resource('dynamodb')  # create connection with the database.

    join_info = event['body']
    logger.info(join_info)
    join_info = json.loads(join_info)
    player_name = join_info["player_name"]
    player_id = join_info["player_id"]
    table_id = join_info["table_id"]
    table = data_base.Table(table_id)  # connect with the table

    connection_id = event["requestContext"].get("connectionId")  # Get connection-ID per client

    # Get players and spectators.
    spectators = table.get_item(Key={'field': "spectators"})['Item']["spectators"]
    players = table.get_item(Key={'field': "players"})['Item']["players"]

    # Check if the client is already a player?
    players_names = [players[p]["player_name"] for p in players]
    if player_name in players_names:
        response = "Already a player"
        
        logger.info("on joined again")

        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }

    # Check if the client is already a spectator?
    if player_name not in spectators:
        spectators[player_name] = connection_id
        table.update_item(Key={'field': 'spectators'},
                          ExpressionAttributeNames={'#u': 'spectators'},
                          UpdateExpression="set #u = :u_map",
                          ExpressionAttributeValues={':u_map': spectators}
                          )
    else:
        # already a spectator but maybe with with different connection id.
        spectators[player_name] = connection_id
        table.update_item(Key={'field': 'spectators'},
                          ExpressionAttributeNames={'#u': 'spectators'},
                          UpdateExpression="set #u = :u_map",
                          ExpressionAttributeValues={':u_map': spectators}
                          )

    # Hide the players' cards.
    for id in players:
        players[id]["card_1"] = "0" if players[id]["card_1"] != "" else ""
        players[id]["card_2"] = "0" if players[id]["card_2"] != "" else ""

    # balance = str(user["balance"])
    balance = "1000"
    logger.info(balance)
    logger.info(players)
    response = build_client_status(table, players)
    response["is_player"] = "0"

    logger.info(response)

    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }


###################################################################################################
# #################################################################################################################

# #####################################
# ########### Data base functions ##########
# #####################################


def get_players(table):
    return table.get_item(Key={'field': "players"})['Item']["players"]  # Get from database.


def get_spectators(table):
    return table.get_item(Key={'field': "spectators"})['Item']["spectators"]  # Get from database.


def get_table_status(table):
    return table.get_item(Key={'field': "table_status"})['Item']  # Get from database.


def get_pots(table):
    return table.get_item(Key={'field': "pots"})['Item']["pots"]  # Get from database.


def calc_pots(pots, players_bets):
    # Players bets are sorted from outside.

    last_pot = len(pots)
    logger.info("pots num:" + str(last_pot))
    # Fill players bets into pots.
    while len(players_bets) != 0:
        last_pot_key = "pot_" + str(last_pot)  # Last pot
        players = sorted([x[0] for x in players_bets])  # Create players.
        bet = players_bets[0][1]  # Get min bet.
        last_pot_players = ["there is no pot yet"]

        if last_pot_key in pots:
            last_pot_players = sorted([int(i) for i in pots[last_pot_key]["players"]])

        if last_pot_players == players:
            pots[last_pot_key]["amount"] = str(bet * len(players) + int(pots[last_pot_key]["amount"]))

        else:
            last_pot += 1
            last_pot_key = "pot_" + str(last_pot)
            pots[last_pot_key] = {}
            pots[last_pot_key]["amount"] = str(bet * len(players))
            pots[last_pot_key]["players"] = {key: key for key in players}

        players_bets = [(s, b - bet) for s, b in players_bets if b - bet > 0]


def update_pots(table, pots):
    table.update_item(Key={'field': "pots"},
                      ExpressionAttributeNames={'#b': 'pots'},
                      UpdateExpression="set #b = :count",
                      ExpressionAttributeValues={':count': pots}
                      )


def reset_bets(players):
    for id in players:
        players[id]["bet"] = "0"


def reset_pots(table):
    update_pots(table, {})


def get_next_round_level(round_level):
    if round_level == "pre_flop":
        return "flop"
    if round_level == "flop":
        return "turn"
    if round_level == "turn":
        return "river"

    return "game ended asdddddddddddddddddddddddddddddddddddddddddddd"


def update_players(table, players):
    table.update_item(Key={'field': "players"},
                      ExpressionAttributeNames={'#b': 'players'},
                      UpdateExpression="set #b = :count",
                      ExpressionAttributeValues={':count': players}
                      )


def update_table_status(table, new_status):
    # Delete old status
    response = table.delete_item(Key={'field': "table_status"})

    # Commit new status
    input = {'field': "table_status", **new_status}
    table.put_item(Item=input)  # Put


round_levels_mapping = {"pre_flop": 0,
                        "flop": 3,
                        "turn": 4,
                        "river": 5}


def build_client_status(table, players):
    # Get info from data base.
    table_status_info = get_table_status(table)
    # players = get_players(table)

    # Response key:
    # bet: last bet.(for client to know which buttons to use).
    # raise: last raise.(for client to know which buttons to use).
    # cards: cards to show on table.
    # bb,sb : big and small blinds.

    # Decide which cards to display.
    round_level = table_status_info["round_level"]
    cards = table_status_info["cards"]
    to_send_cards = {}
    i = 1
    while i <= round_levels_mapping[round_level]:
        key = "card_" + str(i)
        to_send_cards[key] = cards[key]
        i += 1

    # Prepare pots
    pots = get_pots(table)
    pots_to_send = {}
    for i in range(6):
        pot = "pot_" + str(i)
        if pot in pots:
            pots_to_send[pot] = pots[pot]["amount"]

    response = {"action": "table_status",
                "cards": to_send_cards,
                "bet": table_status_info["bet"],
                "raise": table_status_info["raise"],
                "players": players,
                "dealer_pos": table_status_info["dealer_pos"],
                "round_level": table_status_info["round_level"],
                "turn": table_status_info["turn"],
                "pots": pots_to_send,
                "flag": "sendStatus"
                }

    return response
