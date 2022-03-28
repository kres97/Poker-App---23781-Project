# Poker-App---23781-Project





**This repository contains partial implementation of a multiplayer poker mobile application, which
  we have created for university project, and the files contain the server side of the application.**
  
**The application is written for Android devices, but that's not important because we could use any other
  platform for the clients that can open websocket connection, so the server and client can communicate.**
  
**For the server side we used the following Amazon Web Services:**

   - [API Gateway](https://aws.amazon.com/api-gateway/?nc2=type_a)
    
   - [Lambda](https://aws.amazon.com/lambda/)
    
   - [DynamoDB](https://aws.amazon.com/dynamodb/?nc2=type_a)
    
   - [Cloudwatch](https://aws.amazon.com/cloudwatch/?nc2=type_a)

**The game or the poker table isn't a program or process that runs on the cloud, rather it's represented in database (in DynamoDb),
so there is a main procedure or controller on the server that controlls the flow of the game, and it's implemented using Lambda function.
This service (Lambda) enables you to declare and implement your functions, so every lambda "function" has it's own resources, you can 
upload multiple files and must have a handler which runs when the lambda is invoked, in addition when a lambda is invoked an instance of
the lambda is created and starts running on the server.**
**Our lambda functions are:**
- controller
- connect
- join
- sit

**Another note that lambda functions can invoke other lambda functions and execute operations on the database (permissions are needed).**





  
  
