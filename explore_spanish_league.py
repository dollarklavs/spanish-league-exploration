import pandas as pd
import math
from pandasql import sqldf
from bokeh.core.properties import value
from bokeh.plotting import figure, show
from bokeh.io import output_file
from bokeh.models import ColumnDataSource, CDSView, GroupFilter, HoverTool
from bokeh.transform import cumsum, dodge
import bokeh
from bokeh.layouts import row
import pandas_bokeh
pd.set_option('display.max_rows', None, 'display.max_columns', 500)
# pandas_bokeh.output_file('./plots/goals.html')
pysqldf = lambda q: sqldf(q, globals())
team_names = [
        'Barcelona',
        'Real Madrid',
        'Atletico de Madrid',
        'Valencia'
]
team_colors = [
        '#A50044',
        '#E8A7FF',
        '#CB3524',
        '#000000'
]
team_meta = zip(team_names, team_colors)

q = """select 
         case when round = 1
           then season || ' round ' || round
           else round 
         end as season_round
        ,season
        ,round
        ,sum(localGoals) as homegoals
        ,sum(visitorGoals) as awaygoals
       from df
       group by season, round;"""

distinct_team_by_season = """select 
                            season
                           ,division
                           ,localTeam as team 
                           from df
                           group by 
                            season
                           ,division
                           ,localTeam"""

one_season = """select 
                season
                ,division
                ,team
                from team_by_season
                where
                season >= '2017-18'
                and division = '1'"""

all_points_goals = """select
                       'home' venue
                       ,season
                       ,division
                       ,round
                       ,localGoals goalsfor
                       ,visitorGoals goalsagainst
                       ,date
                       ,localTeam team
                       ,visitorTeam againstteam
                       ,case when localGoals > visitorGoals
                          then 3
                        when localGoals = visitorGoals
                          then 1
                        else 0
                        end points
                     from df
                     union all
                     select
                       'away' venue
                       ,season
                       ,division
                       ,round
                       ,visitorGoals goalsfor
                       ,localGoals goalsagainst
                       ,date
                       ,visitorTeam team
                       ,localTeam againstteam
                       ,case when  visitorGoals > localGoals
                          then 3
                        when localGoals = visitorGoals
                          then 1
                        else 0
                        end points
                     from df  """

league_standing = """select
                       team
                      ,sum(goalsfor) forgoals
                      ,sum(goalsagainst) againstgoals
                      ,sum(points) points
                      ,count(*) rounds
                     from points
                     where
                       season = '2017-18'
                     and division = '1'
                     group by
                       team
                     order by
                       points desc
                      ,forgoals desc """
df = pd.read_csv('./data/FMEL_Dataset.csv')
df['date'] = pd.to_datetime(df['timestamp'], origin='unix', unit='s')
goalsdf = pysqldf(q)
goalsdf.set_index(['season_round'])

team_by_season = pysqldf(distinct_team_by_season)
latest_season = pysqldf(one_season)
points = pysqldf(all_points_goals)
points.loc[((points['date'] > '2000-10-31 23:00:00') & points['division'] == '1') & (points['team'].isin(team_names))]
points['date'] = pd.to_datetime(points['date'])
points['goalsfor'] = pd.to_numeric(points['goalsfor'])
points['goalsagainst'] = pd.to_numeric(points['goalsagainst'])
points.sort_values(by=['date'], inplace=True)
points['cum_points'] = points.groupby(['team'])['points'].cumsum()
goalstotal = points[points['division'] == 1].groupby(['season'], as_index=False).sum()
# [['goalsfor',
#                                                      'goalsagainst']].sum()

# goalstotal.loc[goalstotal['division'] == '1']

# transform(pd.Series.cumsum)
# Create ColumnDataSource
points_cds = ColumnDataSource(points)
goalstotal_cds = ColumnDataSource(goalstotal)

# create dictionary with views of each team and color
team_views_colors = { f[0] :
                  (CDSView(source=points_cds,
                           filters=[GroupFilter(column_name='team',
                                                group=f[0])
#                                    ,GroupFilter(column_name='division',
#                                                 group='1')])
                                   ])
                   , f[1])
                  for f in team_meta }

# goals_per_round = CDSView(source=points_cds,
#                           filters=[GroupFilter(column_name='season',
#                                                 group=f[0])
#                                    ,GroupFilter(column_name='division',
#                                                 group='1')])

# initial bokeh figure
eternal_race = figure(x_axis_type='datetime',
                      plot_height=500, plot_width=600,
                      title='Eternal Race', x_axis_label='Date',
                      y_axis_label='Points')

for team, view_color in team_views_colors.items():
    eternal_race.step(x='date', y='cum_points',
                      color=view_color[1], alpha=0.6,
                      legend=team, line_width=2,
                      source=points_cds, view=view_color[0])
eternal_race.legend.location = 'top_left'

goals = figure(plot_height=700, plot_width=1600, x_range=goalstotal['season'],
                      title='GOALS', x_axis_label='Season - Round',
                      y_axis_label='Goals')
goals.xaxis.major_label_orientation = math.pi/2

goals.vbar(x=dodge('season', -0.5, range=goals.x_range), top='goalsfor', width=0.5, bottom=0,
           source=goalstotal_cds, legend=value('GOALS'), color="#718dbf")
goals.vbar(x=dodge('season', 0.0, range=goals.x_range), top='points', width=0.5, bottom=0,
           source=goalstotal_cds, legend=value('POINTS'), color="#e84d60")
# hover = HoverTool(show_arrow=False,
#                       line_policy='nearest',
#                       mode='hline',
#                       tooltips=None)
# hover.tooltips = [
#     ('Venue', '@cum_points'),]
  #  ('Goals for', '@goalsfor'),
  #  ('Goals against', '@goalsagainst'),
  #  ('Opponent', '@againstteam'),
  #  ('Season', '@season'),
  #  ('Date', '@date'),
  #  ('Points', '@cum_points'),
  #  ('Round', '@round'),]
# eternal_race.add_tools(hover)

print(team_by_season)
standing = pysqldf(league_standing)
print(standing)
print(points.loc[(points['team'] == 'Barcelona')])
# print(goalsdf)
print(points['date'].describe())
print(type(points))
print(goalstotal.describe())
print(goalstotal.head())
print(type(goalstotal))
show(row(eternal_race, goals))
