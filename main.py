import random
import bitmex
import lxml
import html5lib
import requests
import ccxt
from bitmex import bitmex
from bitmex_websocket import BitMEXWebsocket
from bs4 import BeautifulSoup
import time
import re
import math
import keyboard
from pynput.keyboard import Key, Listener

pair = str(input("Enter pair: ")).upper()

timeframeselect = str(input('''
Please select timeframe to trade in:
1. 1 minute
2. 5 minute
3. 1 hour
4. 1 day

'''))

if timeframeselect == '1':
    timeframe = '1m'
elif timeframeselect == '2':
    timeframe = '5m'
elif timeframeselect == '3':
    timeframe = '1h'
elif timeframeselect == '4':
    timeframe = '1d'

apikey = ""
secretapikey = ""
upperband = 70
lowerband = 30
period = 14
buycounter = 1
sellcounter = 1
percsafe = 6
percmodrisky = 4
percrisky = 2
percentage = 0
mult = 0
history = []
break_program = False


#login

def login():
    global ws
    global client
    global apikey
    global secretapikey
    global pair

    choice = str(input('''
Login:
1. Enter Login Details
2. Remember Previous Login Details
3. Exit

'''))
    if choice == '1':
        apikey = str(input("Enter your API Key: "))
        secretapikey = str(input("Enter your Secret API Key: "))
        ws = BitMEXWebsocket(endpoint="https://testnet.bitmex.com/api/v1", symbol=pair, api_key=apikey, api_secret=secretapikey)
        client = bitmex(test=True, api_key=apikey, api_secret=secretapikey)
        print('Login Successful \n')

        mainmenu()

    elif choice == '2':
        apikey = '1Bk8AeOWOjO2DCUjFSOFQK11'
        secretapikey = 'crGr--X10duyKqUKKtfgfS5E0FrgsF2jz439eSrHjlkVMgS3'
        connect()
        mainmenu()

    elif choice == '3':
        exit()


def connect():
    global ws
    global client
    print("\nConnecting to BitMex servers...")
    ws = BitMEXWebsocket(endpoint="https://testnet.bitmex.com/api/v1", symbol=pair, api_key=apikey, api_secret=secretapikey)
    client = bitmex(test=True, api_key=apikey, api_secret=secretapikey)
    print("Connection Established \n")


#logout

def logout():
    global logout
    logout = requests.get('https://testnet.bitmex.com/api/v1/user/logout')
    print('\nLogout Successful \n')
    login()


# main menu

def mainmenu():
    global break_program
    choice  = input('''
Main Menu:
1. Start Bot
2. View Balance
3. View Trading History
4. Configure Trade Settings
5. Logout
   
''')
    if choice == '1':
       break_program = False
       startbot()
    elif choice == '2':
       printviewbalance()
    elif choice == '3':
       viewtradinghistory()
    elif choice == '4':
       configuretradesettings()
    elif choice == '5':
       logout()
       login()


#calculate rsi

def getrsi():
    global break_program
    def on_press(key):
        global break_program
        if key == Key.shift:
            break_program = True
            mainmenu()

    with Listener(on_press=on_press) as listener:
        while break_program == False:
            global period
            global timeframe
            global pair
            #apikey = '1Bk8AeOWOjO2DCUjFSOFQK11'
            #secretapikey = 'crGr--X10duyKqUKKtfgfS5E0FrgsF2jz439eSrHjlkVMgS3'
            #ws = BitMEXWebsocket(endpoint="https://testnet.bitmex.com/api/v1", symbol=pair, api_key=apikey, api_secret=secretapikey)
            souparray = []
            closingprices = []

            closingprices.append(float(marketprice()))

            recenttrades = ("https://testnet.bitmex.com/api/v1/trade/bucketed?binSize={}&partial=true&symbol={}&count={}&reverse=true").format(timeframe, pair, str(period+1))
            r = requests.get(recenttrades)
            soup = str(BeautifulSoup(r.content, 'lxml'))
            soup = soup.replace('<html><body><p>[{', '')
            soup = soup.replace('}]</p></body></html>', '')

            soupstring = ""
            slicedsoup = [char for char in soup]
            while True:
                x = 0
                if slicedsoup[x] == '{':
                    del slicedsoup[x]
                    break
                elif slicedsoup[x] != '{':
                    del slicedsoup[x]
            for ele in slicedsoup:
                soupstring += ele

            souparray = soupstring.split(',')
            for x in range(5, len(souparray), 13):
                souparray[x] = re.sub(r'[a-z]+', '', souparray[x], re.I)
                souparray[x] = (souparray[x])[3:]

                closingprices.append(float(souparray[x]))

            closingprices = closingprices[::-1]
            differences = []
            upwardmovement = []
            downwardmovement = []
            for x in range(period):
                differences.append(closingprices[x+1]-closingprices[x])
            for x in differences:
                if x > 0:
                    upwardmovement.append(x)
                    downwardmovement.append(0)
                elif x < 0:
                    downwardmovement.append(abs(x))
                    upwardmovement.append(0)
                elif x == 0:
                    upwardmovement.append(0)
                    downwardmovement.append(0)
            currentavgupwardsmov = sum(upwardmovement) / len(upwardmovement)
            currentavgdownwardsmov = sum(downwardmovement) / len(downwardmovement)
            rs = currentavgupwardsmov / currentavgdownwardsmov
            rsi = 100 - (100/(rs+1))
            return rsi

        listener.join()



# start bot

def determine():
    global sellcounter
    global buycounter
    global mult
    while True:
        time.sleep(10) #to prevent request overload
        if getrsi() <= lowerband and (buycounter == 1): # oversold - buy signal
            mult = 1
            sellcounter = 1
            buycounter = 0
            placeorder()

        if getrsi() >= upperband and (sellcounter == 1): # overbought - sell signal
            mult = -1
            buycounter = 1
            sellcounter = 0
            placeorder()


def startbot():
    global capitalproportion
    global percsafe
    global percmodrisky
    global percrisky
    global percentage
    global risklevel
    global index
    global lowerboundindex
    global upperboundindex
    global period
    global timeframe
    global pair
    # 1. get capitalproportion (this is the amount of BTC to be traded in the next trade)
    # 2. calculate current rsi level using formula
    # 5. if a trade is executed, print the trade showing the following details: ammount in BTC traded, date, time
    # 6. pass every executed trade into the viewtradinghistory function as parameters
    # 1. get capitalproportion (this is the amount of BTC to be traded in the next trade)

    break_program = False
    def on_press(key):
        global break_program
        if key == Key.shift:
            break_program = True
            mainmenu()


    with Listener(on_press=on_press) as listener:
        while break_program == False:
            global capitalproportion
            global percsafe
            global percmodrisky
            global percrisky
            global percentage
            global risklevel
            global index
            global lowerboundindex
            global upperboundindex
            global period
            global timeframe
            global pair

            print("\nBot Running\n")
            print("Press Shift to Stop Bot\n")

            rsi_risk_level = (lowerband / upperband) / period

            risklevel = rsi_risk_level
            index = 0.03061225 #(30/70)/14
            lowerboundindex = index - 0.01785714
            upperboundindex = index + 0.04761905

            if risklevel > lowerboundindex and risklevel < upperboundindex:
                percentage = float(percmodrisky)
            elif risklevel <= lowerboundindex:
                percentage = float(percsafe)
            elif risklevel >= upperboundindex:
                percentage = float(percrisky)

            capitalproportion = int(math.ceil((percentage/100) * (returnviewbalance()*marketprice())))

            determine()

            time.sleep(1)
        listener.join()



def printviewbalance():
    global balance
    #ws = BitMEXWebsocket(endpoint="https://testnet.bitmex.com/api/v1", symbol=pair, api_key=apikey, api_secret=secretapikey)
    funds = dict(ws.funds())
    balance = float(funds['amount'] / 100000000)
    print('\nAvailable Balance: ', balance/100000000, 'BTC')
    choice = str(input("\n3. Back\n"))
    if choice == '3':
        mainmenu()

def returnviewbalance():
    global returnbalance
    #ws = BitMEXWebsocket(endpoint="https://testnet.bitmex.com/api/v1", symbol=pair, api_key=apikey, api_secret=secretapikey)
    returnfunds = dict(ws.funds())
    returnbalance = float(returnfunds['amount'] / 100000000)
    return returnbalance



# view trading history

def viewtradinghistory():
    if len(history) == 0 or None:
        print("No Order History Available")
        goback = str(input("\n3. Back\n"))
        if goback == '3':
            mainmenu()
    else:
        choice = str(input('''
Display Orders By:
1. Newest Trades First
2. Oldest Trades First
3. Back

'''))
        if choice == '1':
            for x in history[::-1]:
                print(x)
            newback = str(input("\n3. Back\n"))
            if newback == '3':
                mainmenu()

        elif choice == '2':
            for x in history:
                print(x)
            oldback = str(input("\n3. Back\n"))
            if oldback == '3':
                mainmenu()

        elif choice == '3':
            mainmenu()


# menu - configure trading settings

def configuretradesettings():
    choice = input('''
Trade Settings:
1. RSI Settings
2. Risk Management Settings
3. Back
    
''')

    if choice == '1':
        rsisettings()
    elif choice == '2':
        riskmanagementsettings()
    elif choice == '3':
        mainmenu()


# rsi settings

def rsisettings():
    choice = str(input('''
RSI Settings:
1. Upper Band
2. Lower Band 
3. Period
4. Back

'''))
    if choice == '1':
        global upperband
        print(("\nUpperband currently set to {}.").format(upperband))
        op1 = str(input('''
Would you like to change the upperband?
1. Yes
2. No
3. Back

'''))
        if op1 == '1':
            upperband = int(input("\nEnter upperband level: "))
            rsisettings()
        elif op1 == '2' or '3':
            rsisettings()

    elif choice == '2':
        global lowerband
        print(("\nLowerband currently set to {}.").format(lowerband))
        op2 = str(input('''
Would you like to change the lowerband?
1. Yes
2. No
3. Back

'''))
        if op2 == '1':
            lowerband = int(input("\nEnter lowerband level: "))
            rsisettings()
        elif op2 == '2' or '3':
            rsisettings()

    elif choice == '3':
        global period
        print(("\nPeriod currently set to {}.").format(period))
        op3 = str(input('''
Would you like to change the period?
1. Yes
2. No
3. Back

'''))
        if op3 == '1':
            period = int(input("\nEnter period level: "))
            rsisettings()
        elif op3 == '2' or '3':
            rsisettings()

    elif choice == '4':
        configuretradesettings()


# menu - risk management settings

def riskmanagementsettings():
    choice = input('''
Risk Management Settings:
1. Risk Level Settings
2. Capital Proportion Management Settings
3. Back
    
''')
    if choice == '1':
        risklevelsetting()
    elif choice == '2':
        capitalproportionmanagementsetting()
    elif choice == '3':
        configuretradesettings()




# manually set risk level

def risklevelsetting():
    global risklevel
    global index
    global lowerboundindex
    global upperboundindex
    global percentage
    global capitalproportion
    global percsafe
    global percmodrisky
    global percrisky
    global period
    global timeframe
    global pair

    rsi_risk_level = (lowerband / upperband) / period

    risklevel = rsi_risk_level
    index = 0.03061225 #(30/70)/14
    lowerboundindex = index - 0.01785714
    upperboundindex = index + 0.04761905

    if risklevel <= lowerboundindex:
        percentage = float(percsafe)
        print('''
Current trading settings are relatively safe.
(Disclaimer: Your capital is always at risk.)
''')
        #capitalproportionmanagementsetting(percsafe)
    elif risklevel > lowerboundindex and risklevel < upperboundindex:
        percentage = float(percmodrisky)
        print('''
Current trading settings are moderately risky.
(Disclaimer: Your capital is always at risk.)
''')
        #capitalproportionmanagementsetting(percmodrisky)
    elif risklevel >= upperboundindex:
        percentage = float(percrisky)
        print('''
Current trading settings are risky.
(Disclaimer: Your capital is always at risk.)
''')
        #capitalproportionmanagementsetting(percrisky)

    choice = str(input('''
Would you like to change trading settings?
1. Yes
2. No
3. Back

'''))
    if choice == '1':
        configuretradesettings()
    elif choice == '2' or '3':
        riskmanagementsettings()




# manually or automatically set proportional of capital per trade - choice made by user

def capitalproportionmanagementsetting():
    global capitalproportion
    global percsafe
    global percmodrisky
    global percrisky
    global percentage
    global risklevel
    global index
    global lowerboundindex
    global upperboundindex
    global period
    global timeframe
    global pair

    rsi_risk_level = (lowerband / upperband) / period

    risklevel = rsi_risk_level
    index = 0.03061225 #(30/70)/14
    lowerboundindex = index - 0.01785714
    upperboundindex = index + 0.04761905

    if risklevel > lowerboundindex and risklevel < upperboundindex:
        percentage = float(percmodrisky)
    elif risklevel <= lowerboundindex:
        percentage = float(percsafe)
    elif risklevel >= upperboundindex:
        percentage = float(percrisky)

    print(("\nCurrent proportion of capital allocated per trade is: {}%").format(percentage))
    capitalproportion = (percentage/100) * returnviewbalance()

    choice = str(input('''
Capital Proportion Management Settings:
1. Capital Proportion for Relatively Safe Trades
2. Capital Proportion for Moderately Risky Trades
3. Capital Proportion for Risky Trades
4. Back    
'''))
    if choice == '1':
        print(("Current capital proportion for relatively safe trades is: {}%").format(percsafe))
        op1 = str(input('''
Would you like to change this proportion?
1. Yes
2. No
3. Back

'''))
        if op1 == '1':
            percsafe = float(input("Enter capital proportion for relatively safe trades (%): "))
            capitalproportionmanagementsetting()
        elif op1 == '2':
            capitalproportionmanagementsetting()
        elif op1 == '3':
            capitalproportionmanagementsetting()

    elif choice == '2':
        print(("Current capital proportion for moderately risky trades is: {}%").format(percmodrisky))
        op2 = str(input('''
Would you like to change this proportion?
1. Yes
2. No
3. Back

'''))
        if op2 == '1':
            percmodrisky = float(input("Enter capital proportion for moderately risky trades (%): "))
            capitalproportionmanagementsetting()
        elif op2 == '2':
            capitalproportionmanagementsetting()
        elif op2 == '3':
            capitalproportionmanagementsetting()


    elif choice == '3':
        print(("Current capital proportion for risky trades is: {}%").format(percrisky))
        op3 = str(input('''
Would you like to change this proportion?
1. Yes
2. No
3. Back

'''))
        if op3 == '1':
            percrisky = float(input("Enter capital proportion for risky trades (%): "))
            capitalproportionmanagementsetting()
        elif op3 == '2':
            capitalproportionmanagementsetting()
        elif op3 == '3':
            capitalproportionmanagementsetting()

    elif choice == '4':
        riskmanagementsettings()



# get market price

def marketprice():
    data = dict(ws.get_instrument())
    marketprice = data['lastPrice']
    return marketprice



# place order

def placeorder():
    global mult
    global order
    global buydatamsg
    global selldatamsg
    global history
    price = marketprice()
    logtime = time.ctime(time.time())
    order = client.Order.Order_new(symbol=pair, orderQty=capitalproportion*mult, price=price).result()
    if capitalproportion*mult > 0:
        buymsg = 'Buy Order Executed'
        print(buymsg)
        buydatamsg = ('{}: Bought {} contract(s) of {} at {}').format(str(logtime), str(capitalproportion), pair, str(price))
        history.append(buydatamsg)
        print(buydatamsg)
    elif capitalproportion*mult < 0:
        sellmsg = 'Sell Order Executed'
        print(sellmsg)
        selldatamsg = ('{}: Sold {} contract(s) of {} at {}').format(str(logtime), str(capitalproportion), pair, str(price))
        history.append(selldatamsg)
        print(selldatamsg)

    time.sleep(60) #waits 1 minute to prevent overload of requests
    determine()

login()
