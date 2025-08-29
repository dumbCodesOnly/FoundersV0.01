# Neon Database Setup for Vercel Deployment

## Step 1: Create Neon Database
1. Go to https://neon.tech
2. Sign up/Login with your GitHub account
3. Create a new project
4. Choose region closest to your users
5. Copy the connection string

## Step 2: Vercel Environment Variables
Set these in your Vercel project settings:

```
DATABASE_URL=postgresql://username:password@host/database?sslmode=require
SESSION_SECRET=your-random-secret-key-here
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
BOT_OWNER_ID=your-telegram-user-id
```

## Step 3: Database Connection String Format
Your Neon connection string should look like:
```
postgresql://[user]:[password]@[neon-hostname]/[database]?sslmode=require
```

## Step 4: Deploy
1. Rename `vercel-requirements.txt` to `requirements.txt`
2. Push to your Git repository
3. Deploy via Vercel dashboard or CLI

## Optimizations Applied
✓ SSL required for Neon connections
✓ Connection pooling optimized for serverless
✓ Automatic table creation on first deployment
✓ Error handling for database initialization
✓ Connection timeout settings for reliability