# Crypto Altcoin Trading Bot

This bot automatically executes trades between BTC and user-specified altcoins to try and realize maximum returns. It operates on the following assumptions: 

 
* During a 'bull run', altcoins outperform BTC
* During a downturn or 'bear run', altcoins lose more value than BTC
* The altcoins specified by the user are on a long-term upward trend

This bot depends on some degree of technical analysis, sentiment analysis, and user 'wisdom'. 

All trades are executed on the Binance exchange.


## Trading Mechanics

This bot relies on three main indicators to decide whether to perform a buy, sell, or no trade. These are: 

1. BTC Market Cap Dominance Percentage
2. BTC Price (in terms of USD)
3. Crypto Fear and Greed Index

The trading loop will check these three values every 60 seconds to evaluate which action should be taken. 

If the algorithm decides it is time to buy, the alt coin with the lowest price in relation to its 30-day simple moving average will be chosen, and a 0.0001 BTC buy order will be created. No buy orders will be created for this coin for the next 24 hours. 

When the algorithm decides to sell, it will do the inverse, and will choose the coin which is trading at the highest price in relation to its 30-day simple moving average. A sell order will be created for either half of that asset's free balance, or the equivalent of 0.0001 BTC, whichever is higher. The algorithm ensures that no coin is sold for less than its average buy price. 

Persistence is ensured by two comma-separated vector files which are automatically created and appended as trades are executed.

Note: This bot tries to maximize reliance on the Binance API to ensure data integrity, but does rely on the CoinMarketCap API for the BTC dominance figure and on alternative.me for the fear/greed index value.

## Config

In the config directory, a config.json file must be provided. It must include (in JSON format):

* Binance API key 
* Binance API secret 
* CoinMarketCap API key
* List of altcoins the user wants to trade. (BTC trading pairs must exist for each coin specified)

A sample config file is provided. The bot assumes a correct config file.  

## Performance

To measure the success of this bot, we look at the percentage gain/loss of the total portfolio value at any given time compared to the value of the initial investment. 

This bot will be deployed with CAD$100 worth of BTC, and its performance metrics will be monitored and made publicly available.

When testing is concluded and the bot is deployed on an AWS EC2 instance, a link will be provided where this data will be available for my configuration. 

Please note that this is not a high-frequency trading bot and so performance should be evaluated on a longer-term basis. 