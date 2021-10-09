# Poker-App---23781-Project





**This repository contains partial implementation of a multiplayer poker mobile application, which
  we have created for university project, and the files contain the cloud side of the application.**
  
**The application is written for Android devices, but that's not important because we could use any other
  platform for the clients that can open websocket connection, so the server and client can communicate.**
  
**For the server side we used the following Amazon Web Services:**

   - [API Gateway](https://aws.amazon.com/api-gateway/?nc2=type_a)
    
   - [Lambda](https://aws.amazon.com/lambda/)
    
   - [DynamoDB](https://aws.amazon.com/dynamodb/?nc2=type_a)
    
   - [Cloudwatch](https://aws.amazon.com/cloudwatch/?nc2=type_a)

**The game or the poker table isn't a program or process that runs on the cloud, but it's represented in database (in DynamoDb),
so there is a main procedure or controller on the cloud that controlls the flow of the game, and it's implemented using Lambda function.
This service (Lambda) enables you to declare and implement your functions, so every lambda "function" has it's own resources, you can 
upload multiple files and must have a handler which runs when the lambda is invoked, in addition when a lambda is invoked an instance of
the lambda is created and starts running on the server.**
**Our lambda functions are:**
- controller
- connect
- join
- sit

**Another note that lambda functions can invoke other lambda functions and execute operations on the database (permissions are needed).**

**Client:**

On connection, the client invokes connect lambda, then invokes join lambda to choose table and enter as spectator,
to play he invokes sit lambda.

**Server:**

The tables are in the database and each table has its own propeties like the ones for the poker logic and also the information of the users. When connect is invoked it saves the websocket connection of the new client.








Back to the controller, which has it's own lambda that implements the main algorithm of the game:

Using Lambda we can create and implement our procedures.
Whenever a lambda function is called, a new instance of the function is created and starts running on the server.
Lambda functions can invoke other lambda functions, and execute operations on the database, so every lambda function has it’s own “role permissions” (for example: reading from database, or invoking other function).

    
    
**
    
 
  
  

  
we will implement a multiplayer poker application by using cloud services.** 








**

 **

  
  
