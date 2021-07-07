import json
import os
import boto3
import os
import logging
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def broadcast_status(players, spectators):
    # Broadcast status if games hasn't started yet.
    URL = "https://ea17g2kd0h.execute-api.eu-west-1.amazonaws.com/test/"  # URL of out API Gateway.
    client = boto3.client("apigatewaymanagementapi", endpoint_url=URL)  # Our server as a "client".

    logger.info("before broadcasting ")

    response = {"action": "table_status",
                "players": players,
                "is_player": "0",
                "dealer_pos": "1",
                "flag": "onSit"
                }

    # Send for all spectators.
    for id in spectators:
        connection_id = spectators[id]
        client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(response))

    # Send for all players
    for id in players:
        connection_id = players[id]["connection_id"]
        response["is_player"] = id
        client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(response))


def lambda_handler(event, context):
    data_base = boto3.resource('dynamodb')  # create connection with the database.

    sit_info = event['body']
    sit_info = json.loads(sit_info)
    player_name = sit_info["player_name"]
    player_id = sit_info["player_id"]
    table_id = sit_info["table_id"]
    table = data_base.Table(table_id)  # connect with the table
    # buy_in = sit_info["buy_in"]
    buy_in = "1000"
    seat = sit_info["seat"]
    connection_id = event["requestContext"].get("connectionId")  # Get connection-ID per client .
    response = player_name + "sat successfully on" + table_id

    logger.info("got here")

    # Get spectators and players.

    spectators = table.get_item(Key={'field': "spectators"})['Item']["spectators"]
    players = table.get_item(Key={'field': "players"})['Item']["players"]

    # Check if seat is already taken.
    if seat in players:
        logger.info("seat already taken")
        client_status = build_client_status(table, players)
        return {
            'statusCode': 200,
            'body': json.dumps(client_status)
        }

    # Move client from specs to players.
    if player_name in spectators:
        # Delete client from specs.
        del spectators[player_name]
        table.update_item(Key={'field': 'spectators'},
                          ExpressionAttributeNames={'#u': 'spectators'},
                          UpdateExpression="set #u = :u_map",
                          ExpressionAttributeValues={':u_map': spectators}
                          )

        # Add client to players.
        players[seat] = {"player_name": player_name, "connection_id": connection_id, "balance": buy_in,
                         "card_1": "", "card_2": "", "status": "fold", "bet": "0", "player_id": player_id}

        table.update_item(Key={'field': 'players'},
                          ExpressionAttributeNames={'#u': 'players'},
                          UpdateExpression="set #u = :u_map",
                          ExpressionAttributeValues={':u_map': players}
                          )

        logger.info("on sit got here 82")

        # Broadcast to all specs and players.
        broadcast_status(players, spectators)

    else:
        response = player_name + " isn't in spectators"
        return {
            'statusCode': 500,
            'body': json.dumps(response)
        }

    table_status_info = table.get_item(Key={'field': "table_status"})['Item']  # Get table status fields.

    logger.info(table_status_info["status"])
    logger.info(len(players))

    # Start game if table status is empty and number of players is 2.
    if table_status_info["status"] == "" and len(players) == 2:
        time.sleep(2)  # be more sure that clients got the previous broadcast.

        logger.info("before starting the game")

        # Initialize table status.
        dealer_pos = seat
        status = "dealing"
        time_stamp = "1"
        # Init status
        table.update_item(Key={'field': "table_status"},
                          ExpressionAttributeNames={'#u': 'dealer_pos'},
                          UpdateExpression="set #u = :u_map",
                          ExpressionAttributeValues={':u_map': dealer_pos}
                          )

        table.update_item(Key={'field': "table_status"},
                          ExpressionAttributeNames={'#u': 'status'},
                          UpdateExpression="set #u = :u_map",
                          ExpressionAttributeValues={':u_map': status}
                          )
        # Init time stamp
        table.update_item(Key={'field': "table_status"},
                          ExpressionAttributeNames={'#u': 'time_stamp'},
                          UpdateExpression="set #u = :u_map",
                          ExpressionAttributeValues={':u_map': time_stamp}
                          )

        input = {"table_id": table_id} ##CHANGED BY NAWRAS , was{"table_id": "table_1"}
        client = boto3.client('lambda')
        client.invoke(
            FunctionName='controller',
            InvocationType='RequestResponse',
            Payload=json.dumps(input)
        )

    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }


################################################################################################
                        # Helper methods.

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
                "flag": "sendStatus",
                "status": table_status_info["status"]
                }

    return response