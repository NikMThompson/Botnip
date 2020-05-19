# Botnip
Discord bot for compiling, tracking, and reporting Animal Crossing New Horizons Turnip prices

### Disclaimer
This bot currently only works in Eastern Timezone. You can change that in the main.py by replacing wherever it uses Eastern Timezone to whatever timezone you want but it currently won't work cross timezone. This is due to how Discord is sending timezone information through it's library. It is a point for possible enhancement in the future.

## How to Deploy
The bot uses dynamoDB as provided by AWS to keep track of all of the prices for the week. You will need to create two files in order to use dyanmoDB with this bot. 
1. **dynamo_accesskey.txt** - go to the AWS management console and then go to the IAM console. Go to Users, create a user if you do not have one already and make sure that the new user has access to dynamoDB. After your user is set up, go to the Security Credentials tab and then the Access Keys section. Create an Access Key and save the access key to dynamo_accesskey.txt.
2. **dynamo_secret.txt** - When you create the secret key it will give you a secret access key as well. Save this to dynamo_secret.txt. You will not be able to see this key again after you close the dialog box so make sure you grab it now. 

Once you have both files saved at the root directory you just need the discord bot token. Create a new discord application and under the _Bot_ settings reveal the token and save it to a new file called **token.txt**. The bot will need to be added to your server as well with the permissions to send messages, manage messages, attach files, read message history, and add reactions.

To host the bot I am using an EC2 instance on AWS. From the EC2 page hit Launch Instance and then select the first option. On the instance type keep the default free tier type and continue. Finally hit launch and you will be prompted to create a new key pair for the instance. Give it a name and then download the key pair which will download a **.pem** file to your default download location. You will need this to access your instance. 

Once your instance is up and running we will connect to it. To do so I tend to use cyberduck. In cyberduck hit open connection and start an SSH FTP connection from the dropdown. For the server you will need to go to your instance and click the checkbox on the left of the table and hit connect at the top. Then a dialog box will open and will have the public DNS that you can use for the server. The username will be ec2-user, there is no password. For the SSH Private Key you will need to find the .pem file you downloaded earlier when you created the key pair.

Once you are connected you can freely move over the files from the root directory into cyberduck and they will be uploaded to the instance.

Then you will need to install python and the necessary libraries onto the instance. In cyberduck you can hit Go and then Open in Putty to get command line access to the instance. First install python with the command sudo yum install python3 and confirm the install when prompted. Next install the discord library with ```sudo python3.7 -m pip install -U discord.py```. Then do the same with the following libraries: 
 - pytz.py
 - pydantic
 - matplotlib

now that it is all installed we need to give permissions for the scripts to run. In the putty file do ```chmod +x main.py```. You can confirm it was done by typing ls and seeing the filename is green.

for the run scripts you might need to fix windows encoding on them. Do this by running ```sudo yum install dos2unix``` and then ```dos2unix run.sh``` and ```dosunix nrun.sh```

Now you need to ```chmod +x run.sh``` and ```chmod +x nrun.sh``` and then you can simply do ```./nrun.sh``` and the bot will run.
