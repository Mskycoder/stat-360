import dash
from datetime import datetime as dt
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go

from components import Column, Header, Row

import mysql.connector


def get_dictionary():
    mydb = mysql.connector.connect(
      host="hackathon-db.bdc.n360.io",
      user="events",
      passwd="", # add api key
      database="hackathon"
    )

    mycursor = mydb.cursor()
    dictionary = dict()
    mycursor.execute("""
        SELECT organization_unit_id, organization_unit_name
        FROM organization_unit
    """)
    res = mycursor.fetchall()
    for tuple in res:
        dictionary[tuple[0]] = tuple[1]

    return dictionary


name_map = get_dictionary()


# Load data
website_df = pd.read_csv('data/website_statistics.csv')
segment_names = website_df.segment_name.value_counts().index.tolist()
website_ids = website_df.website_id.value_counts().index.tolist()

lead_df = pd.read_csv('data/lead.csv')
dealer_list = lead_df.organization_unit_id.tolist()


stats = [
    'avg_session_duration',
    'avg_time_on_page',
    'bounce_rate',
    'bounces',
    'new_user_percentage',
    'new_users',
    'pageviews',
    'pageviews_per_session',
    'percent_new_sessions',
    'session_duration',
    'sessions',
    'time_on_page',
    'users'
]

app = dash.Dash(__name__)
server = app.server  # Expose the server variable for deployments

# Standard Dash app code below
app.layout = html.Div(className='container', children=[

    Header('Interactive Dashboard'),

    Row([
        Column(width=6, children=[
            dcc.Dropdown(
                id='dealer-dropdown',
                options=[
                    {'label': f"{name_map[i]} ({i})", 'value': str(i)}
                    for i in dealer_list
                ],
                value=dealer_list[0]
            ),
            dcc.DatePickerRange(
                id='date-picker-range',
                display_format='Y-M-D',
                min_date_allowed=dt(2017, 1, 1),
                max_date_allowed=dt(2020, 1, 1),
                start_date=dt(2017, 1, 1),
                end_date=dt(2020, 1, 1),
            ),
            dcc.RadioItems(
                id='lead-radio-items',
                options=[
                    {'label': i.replace('_', ' ').title(), 'value': i}
                    for i in ['lead_type', 'lead_status']
                ],
                labelStyle={'display': 'inline-block'},
                value='lead_type'
            ),
            dcc.Graph(id='lead-graph')
        ]),
        Column(width=6, children=[
            dcc.Dropdown(
                id='stats-dropdown',
                options=[
                    {'label': i.replace('_', ' ').title(), 'value': i}
                    for i in stats
                ],
                value=stats[0]
            ),
            dcc.Dropdown(
                id='website-id-dropdown',
                options=[
                    {'label': f"Website #{i}", 'value': str(i)}
                    for i in website_ids
                ],
                value=str(website_ids[0])
            ),
            dcc.Graph(id='website-stats-graph')
        ])
    ])
])


@app.callback(Output('lead-graph', 'figure'),
              [Input('lead-radio-items', 'value'),
               Input('dealer-dropdown', 'value'),
               Input('date-picker-range', 'start_date'),
               Input('date-picker-range', 'end_date')])
def update_lead_graph(col_name, dealer, start_date, end_date):
    source_mask = lead_df['lead_source'] == 'Web'
    start_date_mask = lead_df['date_created'] > start_date
    end_date_mask = lead_df['date_created'] < end_date
    dealer_mask = lead_df['organization_unit_id'] == int(dealer)
    masked_df = lead_df[source_mask & start_date_mask & end_date_mask & dealer_mask]

    pie_data = masked_df[col_name].value_counts()[:10]

    trace1 = go.Pie(
        labels=pie_data.index,
        values=pie_data.values
    )
    layout = go.Layout(
        title=col_name.replace("_", " ").title()
    )
    fig = go.Figure([trace1], layout=layout)

    return fig


@app.callback(Output('website-stats-graph', 'figure'),
              [Input('stats-dropdown', 'value'),
               Input('website-id-dropdown', 'value'),
               Input('date-picker-range', 'start_date'),
               Input('date-picker-range', 'end_date')])
def update_website_stats_graph(stat, website_id, start_date, end_date):
    y_name = stat.replace('_', ' ').title()
    website_id = int(website_id)

    traces = []
    for segment_name in segment_names:
        segment_mask = website_df['segment_name'] == segment_name
        website_mask = website_df['website_id'] == website_id
        start_date_mask = website_df['date_start'] > start_date
        end_date_mask = website_df['date_start'] < end_date
        masked_df = website_df[segment_mask & website_mask & start_date_mask & end_date_mask]

        trace = go.Scatter(
            x=masked_df.date_start.values,
            y=masked_df[stat].values,
            name=segment_name
        )

        traces.append(trace)

    layout = go.Layout(
        title=f"Monthly statistics for Website #{website_id}",
        xaxis=dict(title="Start Date"),
        yaxis=dict(title=y_name)
    )
    fig = go.Figure(traces, layout)

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
