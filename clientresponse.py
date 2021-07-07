

import json
import os
import boto3
import logging
import time
import utils
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# This function updates the table status in database, with the player decision
# Then mark the status as updated, and call a new instance of controller.

def lambda_handler(event, context):




    data_base = boto3.resource('dynamodb')              # create connection with the database.
    body = json.loads(event['body'])  if 'body' in event else event  # Get body.
    table_id = body["table_id"]                         # Get table id for request body.
    table = data_base.Table(table_id)                   # Connect to the table.
    users = data_base.Table('Users')


    connection_id = event["requestContext"].get("connectionId") if 'body' in event else None

    # Get data from data base.
    table_status_info = utils.get_table_status(table)
    players = utils.get_players(table)
    spectators = utils.get_spectators(table)   #ADDED BY NAWRAS

    action = body["player_action"]
    seat = body["seat"]     
    logger.info(seat)

    
    


    # Check client wants to refresh.
    if action == "refresh":
        utils.send_refreshed_status(table, players, seat, connection_id)
        return {
            'statusCode': 200,
            'body': json.dumps('Refreshed status')
        }

    call_bet = int(table_status_info["bet"]) - int(players[seat]["bet"])
    bet = body["bet"] if action != "call" else str(call_bet)


    # Increase time stamp.
    new_time_stamp = str(int(table_status_info["time_stamp"])+1)
    table_status_info["time_stamp"] = new_time_stamp


    # Update bet, balance for player.
    players[seat]["balance"] = str(int(players[seat]["balance"])-int(bet))

    # If
    one_player_left = False

    if action == "fold":
        players[seat]["status"] = "fold"
        players[seat]["card_1"] = ""
        players[seat]["card_2"] = ""

        active_players = utils.get_active_players(players)

        if len(active_players) == 1:

            # update pots.
            pots = utils.get_pots(table)
            players_bets = [(i, int(players[i]["bet"])) for i in players if int(players[i]["bet"]) > 0]

            players_bets.sort(key=lambda x: x[1])

            # Calc and pudate pots into database.
            utils.calc_pots(pots, players_bets)
            utils.update_pots(table, pots)

            # Rest field bet to 0 for all players( new round).
            utils.reset_bets(players)


            # Calculate winning and update players balance.
            utils.calc_winnings(active_players, table_status_info["cards"], pots, players)
            # Update table status
            table_status_info["status"] = "winning"
            # Reset pots
            utils.reset_pots(table)
            one_player_left = True




    elif action == "check":
        players[seat]["status"] = "check"
        
    elif action == "standup":                    #ADDED BY NAWRAS
        
        player_id = body["player_id"]       #ADDED BY NAWRAS
        player_name = body["player_name"]   #ADDED BY NAWRAS
        del players[seat]                        #ADDED BY NAWRAS
        spectators[player_name] = connection_id  #ADDED BY NAWRAS

        active_players = utils.get_active_players(players)
        logger.info(active_players)
        #users[player_id]["balance"] = balance    #ADDED BY NAWRAS

        if len(active_players) == 1:                    #Not just active players, all kinds of players

            # update pots.
            pots = utils.get_pots(table)
            players_bets = [(i, int(players[i]["bet"])) for i in players if int(players[i]["bet"]) > 0]

            players_bets.sort(key=lambda x: x[1])

            # Calc and pudate pots into database.
            utils.calc_pots(pots, players_bets)
            utils.update_pots(table, pots)

            # Rest field bet to 0 for all players( new round).
            utils.reset_bets(players)


            # Calculate winning and update players balance.
            utils.calc_winnings(active_players, table_status_info["cards"], pots, players)
            # Update table status
            table_status_info["status"] = "winning"
            # Reset pots
            utils.reset_pots(table)
            one_player_left = True
        
        if len(players) <= 1:
                table_status_info['status'] = ""
                table_status_info['time'] = ""
                table_status_info['round_level'] = "pre_flop"
                
    
                table.update_item(Key={'field': 'pots'},
                                      ExpressionAttributeNames={'#u': 'pots'},
                                      UpdateExpression="set #u = :u_map",
                                      ExpressionAttributeValues={':u_map': {}  }
                                      ) 
 
                                          
   
                                      
                
    


    elif action == "call":
        players[seat]["status"] = "call"
        players[seat]["bet"] = str(int(bet) + int(players[seat]["bet"]))


    elif action == "bet":
        players[seat]["status"] = "bet"
        table_status_info["raise"] = str(int(bet) - int(table_status_info["bet"]))
        table_status_info["bet"] = bet
        players[seat]["bet"] = bet
        table_status_info["start_seat"] = seat

    elif action == "all_in":
        players[seat]["status"] = "all_in"
        players[seat]["bet"] = bet

        min_bet = table_status_info["bet"]
        if bet > min_bet:
            table_status_info["raise"] = bet - table_status_info["bet"]
            table_status_info["bet"] = bet
            table_status_info["bet"] = bet
            table_status_info["start_seat"] = seat





    if not one_player_left:

        next_seat = utils.get_next_turn(players, table_status_info["turn"])  # todo

        # Check if round has ended?
        if next_seat == table_status_info["start_seat"]:
            # Round has ended
            # update pots.
            pots = utils.get_pots(table)
            players_bets = [(i, int(players[i]["bet"])) for i in players if int(players[i]["bet"]) > 0]


            players_bets.sort(key=lambda x: x[1])


            # Calc and pudate pots into database.
            utils.calc_pots(pots, players_bets)
            utils.update_pots(table, pots)

            # Rest field bet to 0 for all players( new round).
            utils.reset_bets(players)


            # Calculate next turn
            table_status_info["turn"] = utils.get_next_turn(players, table_status_info["dealer_pos"])
            # Reset table status fields: (bet,raise).
            table_status_info["bet"] = "0"
            table_status_info["raise"] = table_status_info["sb"]
            table_status_info["start_seat"] = utils.get_next_turn(players, table_status_info["dealer_pos"])

            # Check if game has ended?
            if table_status_info["round_level"] == "river":
                # Game has ended.

                logger.info("entered river status")
                active_players = {player:players[player] for player in players if players[player]["status"] != "fold"}
                # Calculate winning and update players balance.
                utils.calc_winnings(active_players, table_status_info["cards"], pots, players)
                # Update table status
                table_status_info["status"] = "winning"
                # Reset pots
                utils.reset_pots(table)

            else:
                # Round ended but game still on.
                table_status_info["round_level"] = utils.get_next_round_level(table_status_info["round_level"])

        else:
            # Prepare for next turn
            table_status_info["turn"] = next_seat

    # Update database.
    utils.update_table_status(table, table_status_info)
    utils.update_players(table, players)
    logger.info(players)
    utils.update_spectators(table, spectators)              #ADDED BY NAWRAS
    logger.info(spectators)
    



    # Invoke new instance of controller.
    client = boto3.client('lambda')
    input = {"table_id": table_id}
    #logger.info(input)
    #logger.info(json.dumps(input))
    client.invoke(
        FunctionName='controller',
        InvocationType='RequestResponse',
        Payload=json.dumps(input)
    )

    return {
        'statusCode': 200,
        'body': json.dumps('Client responded and new controller is called!')
    }
