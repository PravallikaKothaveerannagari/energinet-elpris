from flask import Flask, render_template, request
import requests
from datetime import datetime, timedelta
from dateutil import parser
import plotly.graph_objects as go
from plotly.subplots import make_subplots

app = Flask(__name__)

# Constants for additional amounts
ELAFTIFT_AMOUNT = 0.87125
SYSTEMTARIF_AMOUNT = 0.0675
TRANSMISSIONSTARIF_AMOUNT = 0.0725


def get_transportomkostninger_tax(timestamp):
    hour = timestamp.hour
    if hour >= 0 and hour <= 5:
        return 0.0652
    elif hour >= 6 and hour <= 17:
        return 0.0978
    elif hour >= 18 and hour <= 20:
        return 0.2544
    elif hour >= 21 and hour <= 23:
        return 0.0978
    else:
        return 0


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/prices', methods=['POST'])
def get_prices():
    timeframe = request.form['timeframe']
    area_selection = request.form['area_selection']

    response = requests.get('https://api.energidataservice.dk/dataset/Elspotprices?limit=200')
    result = response.json()

    data = {
        'WestDenmark': [],
        'EastDenmark': []
    }

    for record in result.get('records', []):
        price_area = record['PriceArea']
        timestamp_str = record['HourUTC']
        timestamp = parser.parse(timestamp_str) + timedelta(hours=1)  # Adjust to GMT+1 (Central European Time)
        spot_price = float(record['SpotPriceDKK']) / 1000.0  # Convert the spot price to a float and divide by 1000

        if price_area == 'DK1':
            data['WestDenmark'].append((timestamp, spot_price))
        elif price_area == 'DK2':
            data['EastDenmark'].append((timestamp, spot_price))

    current_time = datetime.now().replace(minute=0, second=0, microsecond=0)  # Round down to the nearest hour

    if timeframe == '6':
        prices = data['WestDenmark'] if area_selection == '1' else data['EastDenmark']
        prices = [p for p in prices if p[0] >= current_time and p[0] <= current_time + timedelta(hours=5)]
    elif timeframe == '12':
        prices = data['WestDenmark'] if area_selection == '1' else data['EastDenmark']
        prices = [p for p in prices if p[0] >= current_time and p[0] <= current_time + timedelta(hours=11)]
    elif timeframe == '24':
        prices = data['WestDenmark'] if area_selection == '1' else data['EastDenmark']
        prices = [p for p in prices if p[0] >= current_time and p[0] <= current_time + timedelta(hours=23)]

    formatted_prices = []
    for timestamp, spot_price in prices:
        formatted_timestamp = timestamp.strftime("%H:%M")
        taxes = ELAFTIFT_AMOUNT + SYSTEMTARIF_AMOUNT + TRANSMISSIONSTARIF_AMOUNT + get_transportomkostninger_tax(
            timestamp)
        total_price = spot_price + taxes
        formatted_price = "Spotprice: {:.2f} kWh and Taxes: {:.5f}. Total price = {:.2f} kWh".format(
            spot_price, taxes, total_price)
        formatted_prices.append((formatted_timestamp, formatted_price))

    formatted_prices.reverse()  # Reverse the order of the prices

    # Create the graph
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[t[0] for t in prices], y=[t[1] + taxes for t in prices], name='Price (Spot + Taxes)'))
    fig.update_layout(title_text='Energy Prices', xaxis_title='Time', yaxis_title='Price (kWh)')
    fig.update_xaxes(title_text='Time', tickformat="%H:%M", dtick=3600000)  # Display every hour
    fig.update_yaxes(title_text='Price (kWh)')

    graph = fig.to_html(full_html=False)

    return render_template('prices.html', current_time=current_time.strftime("%d/%m/%Y %H:%M"),
                           timeframe=timeframe, area_selection=area_selection,
                           prices=formatted_prices, graph=graph)


if __name__ == '__main__':
    app.run(debug=False)