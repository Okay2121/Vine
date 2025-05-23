# Deploying Your Solana Memecoin Trading Bot to AWS EC2

This guide walks you through the process of deploying your Telegram bot from Replit to an AWS EC2 instance.

## Prerequisites

1. An AWS account
2. Basic understanding of AWS EC2
3. SSH client (Terminal on Mac/Linux, PuTTY on Windows)
4. Your bot files prepared for deployment

## Step 1: Launch an EC2 Instance

1. Log in to your AWS Management Console
2. Navigate to EC2 dashboard
3. Click "Launch Instance"
4. Choose Ubuntu Server 22.04 LTS (or newer)
5. Select a suitable instance type (t2.micro is sufficient for starting)
6. Configure security groups:
   - Allow SSH (port 22) from your IP
   - Allow HTTP (port 80) and HTTPS (port 443) if you plan to add a web interface
7. Create or select an existing key pair for SSH access
8. Launch the instance

## Step 2: Connect to Your EC2 Instance

Using the SSH key pair you created:

```bash
ssh -i /path/to/your-key.pem ubuntu@your-ec2-public-dns
```

## Step 3: Set Up the Environment

Update your system and install Python:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git
```

## Step 4: Upload Your Bot Files

Option 1: Using SCP (from your local machine):

```bash
scp -i /path/to/your-key.pem -r /path/to/your/bot/* ubuntu@your-ec2-public-dns:~/bot/
```

Option 2: Clone from a Git repository (on EC2 instance):

```bash
git clone https://your-repository-url.git ~/bot
```

## Step 5: Configure Environment Variables

1. Create a `.env` file:

```bash
cd ~/bot
cp .env.example .env
nano .env
```

2. Update the values in the `.env` file with your actual credentials:
   - Add your Telegram bot token
   - Configure your database connection
   - Set admin user ID

## Step 6: Set Up the Database

If you're using PostgreSQL:

```bash
sudo apt install -y postgresql postgresql-contrib
sudo -u postgres psql -c "CREATE USER botuser WITH PASSWORD 'your-password';"
sudo -u postgres psql -c "CREATE DATABASE botdb OWNER botuser;"
```

Make sure to update your DATABASE_URL in the `.env` file with these credentials.

## Step 7: Run Your Bot

Make the start script executable and run it:

```bash
cd ~/bot
chmod +x start.sh
./start.sh
```

## Step 8: Set Up Bot to Run as a Service

To keep your bot running after you disconnect from SSH:

1. Create a systemd service file:

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

2. Add the following configuration:

```
[Unit]
Description=Solana Memecoin Trading Telegram Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/bot
ExecStart=/home/ubuntu/bot/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

4. Check the status:

```bash
sudo systemctl status telegram-bot
```

## Step 9: Monitor Your Bot

To view logs:

```bash
sudo journalctl -u telegram-bot -f
```

## Troubleshooting

- If the bot fails to start, check logs with `sudo journalctl -u telegram-bot`
- Verify all environment variables are set correctly in the .env file
- Check database connectivity
- Ensure the Telegram bot token is valid

## Security Considerations

- Keep your .env file secure and never commit it to public repositories
- Regularly update your system with `sudo apt update && sudo apt upgrade`
- Consider setting up a firewall with `ufw`
- Set up automated backups for your database