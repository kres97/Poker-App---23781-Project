import json
import os
import boto3
import logging
import time
import random

import utils

logger = logging.getLogger()
logger.setLevel(logging.INFO)

time_out = 10 * 60  # controller max run time is 10 minutes.


def deal(table):


    # Get deck from database.
    deck = table.get_item(Key={'field': "deck"})['Item']["deck"]
    # Shuffle deck.
    utils.shuffle_deck(deck)

    # Deal table cards.
    cards = {"card_1": deck["1"],
             "card_2": deck["2"],
             "card_3": deck["3"],
             "card_4": deck["4"],
             "card_5": deck["5"]
             }

    # Get spectators and players.
    players = utils.get_players(table)

    # Get table status from database.
    table_status_info = table.get_item(Key={'field': "table_status"})['Item']
    dealer_pos = table_status_info["dealer_pos"]


    # Get positions
    logger.info("dealer pos")
    logger.info(dealer_pos)
    logger.info([id for id in players])
    dealer_pos, sb_pos, bb_pos, turn = utils.update_dealer_postion(int(dealer_pos), sorted([int(id) for id in players]))

    # logger.info(players)  # Debugging

    # Deal cards for players.
    utils.deal_for_players(deck=deck, players=players)

    # Update bets (sb,bb)
    players[sb_pos]["bet"] = table_status_info["sb"]
    players[bb_pos]["bet"] = table_status_info["bb"]
    # Update players balances.
    players[sb_pos]["balance"] = str(int(players[sb_pos]["balance"])-int(table_status_info["sb"]))
    players[bb_pos]["balance"] = str(int(players[bb_pos]["balance"])-int(table_status_info["bb"]))

    # Commit to database.
    table.update_item(Key={'field': 'players'},
                      ExpressionAttributeNames={'#u': 'players'},
                      UpdateExpression="set #u = :u_map",
                      ExpressionAttributeValues={':u_map': players}
                      )

    # Update dealer position, raise, bet.
    table_status_info["dealer_pos"] = dealer_pos
    table_status_info["raise"] = table_status_info["bb"]
    table_status_info["bet"] = table_status_info["bb"]
    table_status_info["round_level"] = "pre_flop"
    table_status_info["cards"] = cards
    table_status_info["turn"] = turn
    table_status_info["start_seat"] = turn
    table_status_info["status"] = ""  # todo what status it should be.

    utils.update_table_status(table, table_status_info)  # Commit to database.




def round():
    pass

def choose_winner():
    pass
##############################################################################################

# case_handlers = {"dealing": deal,
#                  "pre_flop":round,
#                  "flop": round,
#                  "turn":round,
#                  "river":round,
#                  "choose_winner":choose_winner
#                  }


def lambda_handler(event, context):
    # Save start time, so after ten minutes stop and run, and call the function again.
    start_time = time.time()

    data_base = boto3.resource('dynamodb')  # create connection with the database.
    table_id = event["table_id"]  # Get table id for request body.
    table = data_base.Table(table_id)  # Connect to the table.
    players = utils.get_players(table)

    while True:
        current_time = time.time()
        controller_run_time = current_time - start_time

        if controller_run_time >= time_out:
            # Invoke new instance of controller.
            client = boto3.client('lambda')
            intput = {"table_id": table_id} ##CHANGEEEEEEEEEEEEEEEEEEEEEEEEEED
            client.invoke(
                FunctionName='controller',
                InvocationType='RequestResponse',
                Payload=json.dumps(input)
            )
            return {
                'statusCode': 200,
                'body': json.dumps('Controller timed out, calling new instance!')
            }

        # Get table status
        table_status_info = table.get_item(Key={'field': "table_status"})['Item']  # Get table status fields.
        table_status = table_status_info["status"]  # Get table status to know what to do.
        last_update_time_stamp = table_status_info["time_stamp"]  # Save time stamp for later.


        if table_status == "dealing":
            deal(table)

        if table_status == "winning":
            logger.info("reached winning state")

        utils.broadcast(table, table_status)

        logger.info("returned from broadcast")

        logger.info(table_status)
        

        # If status is winning, wait for client to display the result.
        if table_status == "winning":
                

            time.sleep(4)  # Let player enjoy the winnings display :)
            
            if len(players) == 1:
                    return {
                            'statusCode': 200,
                            'body': json.dumps('No Enough Players')
                            }
                 

            # Update status to "dealing", for next round.
            table.update_item(Key={'field': "table_status"},
                              ExpressionAttributeNames={'#b': 'status'},
                              UpdateExpression="set #b = :count",
                              ExpressionAttributeValues={':count': "dealing"}
                              )

            table.update_item(Key={'field': "table_status"},
                              ExpressionAttributeNames={'#b': 'round_level'},
                              UpdateExpression="set #b = :count",
                              ExpressionAttributeValues={':count': "pre_flop"}
                              )

            # Break, so controller begins new round (like invoking controller again).
            continue
        
        
        

        # Wait for client response : sleep for 10 seconds.
        time.sleep(30)

        table_status_info = table.get_item(Key={'field': "table_status"})['Item']  # Get table status fields.
        new_time_stamp = table_status_info["time_stamp"]

        if last_update_time_stamp == new_time_stamp:
            # Invoke client response handler with action fold.
            client = boto3.client('lambda')
            seat = table_status_info["turn"]
            input = {"action": "clientresponse",
                     "table_id": table_id,                                       #changeddddddddddddddddddd
                     "player_action": "fold", "seat": seat, "bet": "0"}

            client.invoke(
                FunctionName='clientresponse',
                InvocationType='RequestResponse',
                Payload=json.dumps(input)
            )


            break
        
        
        
        
        else:
            # Client responded so end the run.
            break

    return {
        'statusCode': 200,
        'body': json.dumps('Controller operated successfully, and client responded!')
    }

