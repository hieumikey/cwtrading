from django.shortcuts import render
from django.http import HttpResponse
from .forms import Covercallstrate
from .models import CoverCallStrate
from .forms import Closeprice
from .models import ClosePrice
from .forms import Cwprice, Covercallbt
from .models import CWPrice, CoverCallBt
import numpy as np
import scipy.stats as si
import sympy as sy
from sympy.stats import Normal, cdf
from sympy import init_printing
import pandas as pd
from datetime import datetime, timedelta
import math
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from io import BytesIO
import base64
import statistics
import time
init_printing()
# Create your views here.

def call_option_price(S, K, t, r, sigma):
    d1 = [np.log(S / K) + (r + ((sigma**2) / 2)) * t] / (sigma * np.sqrt(t))
    d2 = d1 - sigma * np.sqrt(t)
    call_price = S * si.norm.cdf(d1, 0.0, 1.0) - K * np.exp(-r * t) *  si.norm.cdf(d2, 0.0, 1.0)
    return call_price, si.norm.cdf(d1, 0.0, 1.0)[0]

def put_option_price(S, K, t, r, sigma):
    d1 = [np.log(S / K) + (r + ((sigma**2) / 2)) * t] / (sigma * np.sqrt(t))
    d2 = d1 - sigma * np.sqrt(t)
    put_price = K * np.exp(-r * t)*si.norm.cdf(-d2, 0.0, 1.0) - S * si.norm.cdf(-d1, 0.0, 1.0)
    return put_price

def save_covercall(request):
    if request.method == "POST":
        data = Covercallstrate(request.POST)
        if data.is_valid():
            startDate = data.cleaned_data['startDate']
            endDate = data.cleaned_data['endDate']
            symbol = data.cleaned_data['symbol']
            covercall = CoverCallStrate(assetPrice = data.cleaned_data['assetPrice'],
                strikePrice = data.cleaned_data['strikePrice'],
                maturity = data.cleaned_data['maturity'],
                rate = data.cleaned_data['rate'],
                startDate = data.cleaned_data['startDate'],
                endDate = data.cleaned_data['endDate'],
                symbol = data.cleaned_data['symbol'])
            covercall.save()
            volatility = get_volatility(startDate, endDate, symbol)
            call, deltaOptions = call_option_price(data.cleaned_data['assetPrice'], data.cleaned_data['strikePrice'],
                data.cleaned_data['maturity'], data.cleaned_data['rate'], volatility)
            put = put_option_price(data.cleaned_data['assetPrice'], data.cleaned_data['strikePrice'],
                data.cleaned_data['maturity'], data.cleaned_data['rate'], volatility)
            tradeDate = get_date(startDate, endDate, symbol)
            prices = get_price(startDate, endDate, symbol)
            prices = prices.to_numpy()
            plt.plot(tradeDate, prices, color='green', label='prices')
            plt.title('Prices figures:')
            plt.xlabel('Timestamp')
            plt.ylabel('Prices')
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            graphic = base64.b64encode(image_png)
            graphic = graphic.decode('utf-8')
            fdateCW = CWPrice.objects.values('dateCW').first()
            fdateCW = list(fdateCW.values())[0].strftime("%d-%m-%Y")
            ldateCW = CWPrice.objects.values('dateCW').last()
            ldateCW = list(ldateCW.values())[0].strftime("%d-%m-%Y")
            return render(request, 'covercall/campaign.html', {'assetPrice': data.cleaned_data['assetPrice'], 
                'strikePrice':  data.cleaned_data['strikePrice'], 'graphic': graphic, 'fdateCW': fdateCW, 
                'ldateCW': ldateCW, 'call': call[0], 'deltaOptions': deltaOptions, 'volatility': volatility, 'put': put[0] })
        else:
            return HttpResponse('Bad Request')

def show_symbol(request):
    symbols = ClosePrice.objects.values('symbol').distinct()
    return render(request, 'covercall/symbol.html', {'symbols': symbols})

def get_date(startDate, endDate, symbol):
    tradeDate = ClosePrice.objects.filter(symbol = symbol).values('date')
    tradeDate = tradeDate.filter(date__gte = startDate, date__lte = endDate)
    tradeDate = list(tradeDate)
    list_date = []
    for index, date in enumerate(tradeDate):
        list_date.append(tradeDate[index]['date'])
    for index, date in enumerate(list_date):
        list_date[index] = datetime.strftime(list_date[index], "%d-%m-%Y") 
    return np.array(list_date)

def get_price(startDate, endDate, symbol):
    closeprice =  ClosePrice.objects.filter(symbol = symbol).values('closePrice')
    closeprice = closeprice.filter(date__gte = startDate, date__lte = endDate)
    arr_price = np.zeros(len(closeprice), )
    for index, price in enumerate(closeprice):
        arr_price[index] = price['closePrice']
    s_price = pd.Series(arr_price)
    return s_price

def calculate_volatility(data):
    logPrice = np.log(data / data.shift(1))
    daily_std =  np.std(logPrice)
    return daily_std * 252 ** 0.5

def get_volatility(startDate, endDate, symbol):
    volatility = calculate_volatility(get_price(startDate, endDate, symbol))
    return volatility 

def index(request, symbol):
    covercall = Covercallstrate
    return render(request, 'covercall/index.html', {'covercall': covercall, 'symbol': symbol})

def backtest(request):
    if request.method == "POST":
        data = Covercallbt(request.POST)
        #return render(request, 'covercall/backtest.html', {'data': data})
        if data.is_valid():
            startdateBt = data.cleaned_data['startdateBt']
            enddateBt = data.cleaned_data['enddateBt']
            timerange = data.cleaned_data['timerange']
            c = data.cleaned_data['c']
            m = data.cleaned_data['m']
            n = data.cleaned_data['n']
            covercallbacktest = CoverCallBt(startdateBt = data.cleaned_data['startdateBt'],
                enddateBt = data.cleaned_data['enddateBt'],
                timerange = data.cleaned_data['timerange'],
                c = data.cleaned_data['c'],
                m = data.cleaned_data['m'],
                n = data.cleaned_data['n'])
            covercallbacktest.save()
            listV, listDate, CWdate = portfolio_value(startdateBt, enddateBt, c, m, n)
            listReturns = getReturns(listV)
            # index = 0
            # while(index < len(CWdate)):
            #     for i in range(index, index + 10, index + 1):
            
            plt.plot(listDate, listReturns, color='green', label='prices')
            plt.title('Log returns:')
            plt.xlabel('Date')
            plt.ylabel('Returns')
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            graphicV = base64.b64encode(image_png)
            graphicV = graphicV.decode('utf-8')
            return render(request, 'covercall/backtest.html', {'c': data.cleaned_data['c'],
                'startDate': data.cleaned_data['startdateBt'], 'endDate': data.cleaned_data['enddateBt'],
                'timerange': data.cleaned_data['timerange'], 'listV': listV, 'listReturns': listReturns,
                'graphicV': graphicV})
        else:
            return HttpResponse('Bad Request')

def getV(c, m, n, s):
    return n*s - m*c

def portfolio_value(startDate, endDate, c, m , n):
    tradeDate = CWPrice.objects.filter(dateCW__gte = startDate, dateCW__lte = endDate).values('dateCW')
    tradeDate = list(tradeDate.values())
    CWdate = []
    for date in tradeDate:
        CWdate.append(date['dateCW'].strftime("%Y-%m-%d"))
    listDate = []
    for date in tradeDate:
        listDate.append(date['dateCW'].strftime("%m-%d"))
    listV = []
    for index, date in enumerate(CWdate):
        s = CWPrice.objects.filter(dateCW = date).values('closePriceCW')
        listV.append(getV(c, m, n, s[0]['closePriceCW']))
    return np.array(listV), np.array(listDate), np.array(CWdate)

def getReturns(val):
    logReturns = []
    for i, v in enumerate(val):
        logReturns.append(val[i]/val[0])
    return np.array(logReturns)

