import copy

import pytest

from mindsdb_sql import parse_sql
from mindsdb_sql.exceptions import PlanningException
from mindsdb_sql.parser.ast import *
from mindsdb_sql.parser.dialects.mindsdb.latest import Latest
from mindsdb_sql.planner import plan_query
from mindsdb_sql.planner.query_plan import QueryPlan
from mindsdb_sql.planner.step_result import Result
from mindsdb_sql.planner.steps import *
from mindsdb_sql.parser.utils import JoinType


class TestJoinTimeseriesPredictor:
    def test_join_predictor_timeseries(self):
        predictor_window = 10
        group_by_column = 'vendor_id'
        query = Select(targets=[Star()],
                       from_table=Join(left=Identifier('mysql.data.ny_output', alias=Identifier('ta')),
                                       right=Identifier('mindsdb.tp3', alias=Identifier('tb')),
                                       join_type='left join'),
                       )

        expected_plan = QueryPlan(
            steps=[
                FetchDataframeStep(integration='mysql',
                                   query=Select(targets=[Identifier(parts=['ta', group_by_column], alias=Identifier(group_by_column))],
                                                from_table=Identifier('data.ny_output', alias=Identifier('ta')),
                                                distinct=True,
                                                )
                                   ),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(integration='mysql',
                                   query=parse_sql("SELECT * FROM data.ny_output AS ta\
                                    WHERE ta.pickup_hour is not null and ta.vendor_id = '$var[vendor_id]' ORDER BY ta.pickup_hour DESC")
                                   ),
                              ),
                ApplyTimeseriesPredictorStep(namespace='mindsdb',
                                             predictor=Identifier('tp3', alias=Identifier('tb')),
                                             dataframe=Result(1)),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql'],
                          predictor_namespace='mindsdb',
                          predictor_metadata={
                              'tp3': {'timeseries': True,
                                       'order_by_column': 'pickup_hour',
                                       'group_by_columns': [group_by_column],
                                       'window': predictor_window}
                          })

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_join_predictor_timeseries_other_ml(self):
        predictor_window = 10
        group_by_column = 'vendor_id'
        query = parse_sql('select * from mysql.data.ny_output ta'
                          ' left join mlflow.tp3 tb')


        expected_plan = QueryPlan(
            steps=[
                FetchDataframeStep(integration='mysql',
                                   query=Select(targets=[
                                       Identifier(parts=['ta', group_by_column], alias=Identifier(group_by_column))],
                                                from_table=Identifier('data.ny_output', alias=Identifier('ta')),
                                                distinct=True,
                                                )
                                   ),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(integration='mysql',
                                                      query=parse_sql("SELECT * FROM data.ny_output AS ta\
                                       WHERE ta.pickup_hour is not null and ta.vendor_id = '$var[vendor_id]' ORDER BY ta.pickup_hour DESC")
                                                      ),
                              ),
                ApplyTimeseriesPredictorStep(namespace='mlflow',
                                             predictor=Identifier('tp3', alias=Identifier('tb')),
                                             dataframe=Result(1)),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql', 'mlflow'],
                          predictor_metadata=[
                              {'timeseries': True,
                               'name':'tp3',
                               'integration_name': 'mlflow',
                               'order_by_column': 'pickup_hour',
                               'group_by_columns': [group_by_column],
                               'window': predictor_window}
                          ])

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_join_predictor_timeseries_select_table_columns(self):
        predictor_window = 10
        group_by_column = 'vendor_id'
        query = Select(targets=[Identifier('ta.target', alias=Identifier('y_true')),
                                Identifier('tb.target', alias=Identifier('y_pred'))],
                       from_table=Join(left=Identifier('mysql.data.ny_output', alias=Identifier('ta')),
                                       right=Identifier('mindsdb.tp3', alias=Identifier('tb')),
                                       join_type='left join'),
                       )

        expected_plan = QueryPlan(
            steps=[
                FetchDataframeStep(integration='mysql',
                                   query=Select(targets=[Identifier(parts=['ta', group_by_column], alias=Identifier(group_by_column))],
                                                from_table=Identifier('data.ny_output', alias=Identifier('ta')),
                                                distinct=True,
                                                )
                                   ),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(integration='mysql',
                                   query=parse_sql("SELECT * FROM data.ny_output AS ta\
                                    WHERE ta.pickup_hour is not null and ta.vendor_id = '$var[vendor_id]' ORDER BY ta.pickup_hour DESC")
                                   ),
                              ),
                ApplyTimeseriesPredictorStep(namespace='mindsdb',
                                             predictor=Identifier('tp3', alias=Identifier('tb')),
                                             dataframe=Result(1)),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Identifier('ta.target', alias=Identifier('y_true')), Identifier('tb.target', alias=Identifier('y_pred'))]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql'],
                          predictor_namespace='mindsdb',
                          predictor_metadata={
                              'tp3': {'timeseries': True,
                                       'order_by_column': 'pickup_hour',
                                       'group_by_columns': [group_by_column],
                                       'window': predictor_window}
                          })

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_join_predictor_timeseries_query_with_limit(self):
        predictor_window = 10
        group_by_column = 'vendor_id'
        query = Select(targets=[Star()],
                       from_table=Join(left=Identifier('mysql.data.ny_output', alias=Identifier('ta')),
                                       right=Identifier('mindsdb.tp3', alias=Identifier('tb')),
                                       join_type='left join'),
                       limit=Constant(1000),
                       )

        expected_plan = QueryPlan(
            steps=[
                FetchDataframeStep(integration='mysql',
                                   query=Select(targets=[
                                       Identifier(parts=['ta', group_by_column], alias=Identifier(group_by_column))],
                                                from_table=Identifier('data.ny_output', alias=Identifier('ta')),
                                                distinct=True,
                                                )
                                   ),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(
                                  integration='mysql',
                                  query=parse_sql("SELECT * FROM data.ny_output AS ta\
                                   WHERE ta.pickup_hour is not null and ta.vendor_id = '$var[vendor_id]' ORDER BY ta.pickup_hour DESC")
                              ),
                ),
                ApplyTimeseriesPredictorStep(namespace='mindsdb',
                                             predictor=Identifier('tp3', alias=Identifier('tb')),
                                             dataframe=Result(1)),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                LimitOffsetStep(dataframe=Result(3), limit=query.limit),
                ProjectStep(dataframe=Result(4), columns=[Star()]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql'],
                          predictor_namespace='mindsdb',
                          predictor_metadata={
                              'tp3': {'timeseries': True,
                                       'order_by_column': 'pickup_hour',
                                       'group_by_columns': [group_by_column],
                                       'window': predictor_window}
                          })

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_join_predictor_timeseries_filter_by_group_by_column(self):
        predictor_window = 10
        group_by_column = 'vendor_id'
        query = Select(targets=[Star()],
                       from_table=Join(left=Identifier('mysql.data.ny_output', alias=Identifier('ta')),
                                       right=Identifier('mindsdb.tp3', alias=Identifier('tb')),
                                       join_type='left join'),
                       where=BinaryOperation('=', args=[Identifier('ta.vendor_id'), Constant(1)]),
                       )

        expected_plan = QueryPlan(
            steps=[
                FetchDataframeStep(integration='mysql',
                                   query=Select(targets=[
                                       Identifier(parts=['ta', group_by_column], alias=Identifier(group_by_column))],
                                                from_table=Identifier('data.ny_output', alias=Identifier('ta')),
                                                where=BinaryOperation('=', args=[Identifier('ta.vendor_id'), Constant(1)]),
                                                distinct=True,
                                                )
                                   ),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(
                                  integration='mysql',
                                  query=parse_sql("SELECT * FROM data.ny_output AS ta\
                                     WHERE ta.vendor_id = 1 AND ta.pickup_hour is not null and ta.vendor_id = '$var[vendor_id]' \
                                     ORDER BY ta.pickup_hour DESC")
                              ),
                ),
                ApplyTimeseriesPredictorStep(namespace='mindsdb',
                                             predictor=Identifier('tp3', alias=Identifier('tb')),
                                             dataframe=Result(1)),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql'],
                          predictor_namespace='mindsdb',
                          predictor_metadata={
                              'tp3': {'timeseries': True,
                                       'order_by_column': 'pickup_hour',
                                       'group_by_columns': [group_by_column],
                                       'window': predictor_window}
                          })

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_join_predictor_timeseries_latest(self):
        predictor_window = 5
        group_by_column = 'vendor_id'
        query = Select(targets=[Star()],
                       from_table=Join(left=Identifier('mysql.data.ny_output', alias=Identifier('ta')),
                                       right=Identifier('mindsdb.tp3', alias=Identifier('tb')),
                                       join_type=JoinType.LEFT_JOIN,
                                       implicit=True),
                       where=BinaryOperation('and', args=[
                           BinaryOperation('>', args=[Identifier('ta.pickup_hour'), Latest()]),
                           BinaryOperation('=', args=[Identifier('ta.vendor_id'), Constant(1)]),
                       ]),
                       )

        expected_plan = QueryPlan(
            steps=[
                FetchDataframeStep(integration='mysql',
                                   query=Select(targets=[
                                       Identifier(parts=['ta', group_by_column], alias=Identifier(group_by_column))],
                                       from_table=Identifier('data.ny_output', alias=Identifier('ta')),
                                       where=BinaryOperation('=', args=[Identifier('ta.vendor_id'), Constant(1)]),
                                       distinct=True,
                                   )
                                   ),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(
                                  integration='mysql',
                                  query=parse_sql(f"SELECT * FROM data.ny_output AS ta\
                                    WHERE ta.vendor_id = 1 AND ta.pickup_hour is not null and ta.vendor_id = '$var[vendor_id]'\
                                    ORDER BY ta.pickup_hour DESC LIMIT {predictor_window}")
                                                      ),
                              ),
                ApplyTimeseriesPredictorStep(
                    output_time_filter=BinaryOperation('>', args=[Identifier('ta.pickup_hour'), Latest()]),
                    namespace='mindsdb',
                    predictor=Identifier('tp3', alias=Identifier('tb')),
                    dataframe=Result(1),
                ),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql'],
                          predictor_namespace='mindsdb',
                          predictor_metadata={
                              'tp3': {'timeseries': True,
                                      'order_by_column': 'pickup_hour',
                                      'group_by_columns': [group_by_column],
                                      'window': predictor_window}
                          })

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_join_predictor_timeseries_between(self):
        predictor_window = 5
        group_by_column = 'vendor_id'
        query = parse_sql("SELECT * FROM mysql.data.ny_output AS ta\
                                        left join mindsdb.tp3 AS tb\
                           WHERE ta.pickup_hour BETWEEN 1 AND 10 AND ta.vendor_id = 1")

        expected_plan = QueryPlan(
            steps=[
                FetchDataframeStep(integration='mysql',
                                   query=parse_sql("SELECT DISTINCT ta.vendor_id AS vendor_id FROM data.ny_output AS ta\
                                                   WHERE ta.vendor_id = 1")
                                   ),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=MultipleSteps(
                                  reduce='union',
                                  steps=[
                                      FetchDataframeStep(
                                          integration='mysql',
                                          query=parse_sql(f"SELECT * FROM data.ny_output AS ta \
                                          WHERE ta.pickup_hour < 1 AND ta.vendor_id = 1 and ta.pickup_hour is not null \
                                          AND ta.vendor_id = '$var[vendor_id]' \
                                          ORDER BY ta.pickup_hour DESC LIMIT {predictor_window}"),
                                      ),
                                      FetchDataframeStep(
                                          integration='mysql',
                                          query=parse_sql("SELECT * FROM data.ny_output AS ta\
                                           WHERE ta.pickup_hour BETWEEN 1 AND 10 AND ta.vendor_id = 1 and ta.pickup_hour is not null \
                                            AND ta.vendor_id = '$var[vendor_id]' ORDER BY ta.pickup_hour DESC"),
                                      ),

                                  ]
                              )),
                ApplyTimeseriesPredictorStep(
                    output_time_filter=BetweenOperation(
                        args=[Identifier('ta.pickup_hour'), Constant(1), Constant(10)],
                    ),
                    namespace='mindsdb',
                    predictor=Identifier('tp3', alias=Identifier('tb')),
                    dataframe=Result(1),
                ),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql'],
                          predictor_namespace='mindsdb',
                          predictor_metadata={
                              'tp3': {'timeseries': True,
                                      'order_by_column': 'pickup_hour',
                                      'group_by_columns': [group_by_column],
                                      'window': predictor_window}
                          })

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_join_predictor_timeseries_concrete_date_greater(self):
        predictor_window = 10
        group_by_column = 'vendor_id'

        sql = "select * from mysql.data.ny_output as ta left join mindsdb.tp3 as tb where ta.pickup_hour > 10 and ta.vendor_id = 1"

        query = parse_sql(sql, dialect='mindsdb')

        expected_plan = QueryPlan(
            steps=[
                FetchDataframeStep(integration='mysql',
                                   query=Select(targets=[
                                       Identifier(parts=['ta', group_by_column], alias=Identifier(group_by_column))],
                                       from_table=Identifier('data.ny_output', alias=Identifier('ta')),
                                       where=BinaryOperation('=', args=[Identifier('ta.vendor_id'), Constant(1)]),
                                       distinct=True,
                                   )
                                   ),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=MultipleSteps(
                                  reduce='union',
                                  steps=[
                                      FetchDataframeStep(
                                          integration='mysql',
                                          query=parse_sql(f"SELECT * FROM data.ny_output AS ta \
                                          WHERE ta.pickup_hour <= 10 AND ta.vendor_id = 1 and ta.pickup_hour is not null \
                                          AND ta.vendor_id = '$var[vendor_id]' ORDER BY ta.pickup_hour DESC LIMIT {predictor_window}"),
                                      ),
                                      FetchDataframeStep(
                                          integration='mysql',
                                          query=parse_sql("SELECT * FROM data.ny_output AS ta \
                                          WHERE ta.pickup_hour > 10 AND ta.vendor_id = 1 and ta.pickup_hour is not null \
                                          AND ta.vendor_id = '$var[vendor_id]' ORDER BY ta.pickup_hour DESC"),
                                      ),

                                  ]
                              )),
                ApplyTimeseriesPredictorStep(output_time_filter=BinaryOperation('>', args=[Identifier('ta.pickup_hour'), Constant(10)]),
                                             namespace='mindsdb',
                                             predictor=Identifier('tp3', alias=Identifier('tb')),
                                             dataframe=Result(1)),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql'],
                          predictor_namespace='mindsdb',
                          predictor_metadata={
                              'tp3': {'timeseries': True,
                                       'order_by_column': 'pickup_hour',
                                       'group_by_columns': [group_by_column],
                                       'window': predictor_window}
                          })

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_join_predictor_timeseries_concrete_date_greater_2_group_fields(self):
        predictor_window = 10

        sql = "select * from mysql.data.ny_output as ta left join mindsdb.tp3 as tb\
            where ta.pickup_hour > 10 and ta.vendor_id = 1 and ta.type = 2"

        query = parse_sql(sql, dialect='mindsdb')

        expected_plan = QueryPlan(
            steps=[
                FetchDataframeStep(
                    integration='mysql',
                    query=parse_sql('''
                         select distinct ta.vendor_id as vendor_id, ta.type as type
                         from data.ny_output as ta
                         where ta.vendor_id = 1 and ta.type = 2
                       ''')
                ),
                MapReduceStep(
                    values=Result(0),
                    reduce='union',
                    step=MultipleSteps(
                        reduce='union',
                        steps=[
                            FetchDataframeStep(
                                integration='mysql',
                                query=parse_sql(f"SELECT * FROM data.ny_output AS ta \
                                  WHERE ta.pickup_hour <= 10 AND ta.vendor_id = 1 and ta.type = 2 and ta.pickup_hour is not null \
                                  AND ta.vendor_id = '$var[vendor_id]' AND ta.type = '$var[type]'\
                                  ORDER BY ta.pickup_hour DESC LIMIT {predictor_window}"),
                            ),
                            FetchDataframeStep(
                                integration='mysql',
                                query=parse_sql("SELECT * FROM data.ny_output AS ta \
                                  WHERE ta.pickup_hour > 10 AND ta.vendor_id = 1 and ta.type = 2 and ta.pickup_hour is not null \
                                  AND ta.vendor_id = '$var[vendor_id]' AND ta.type = '$var[type]'\
                                  ORDER BY ta.pickup_hour DESC"),
                            ),

                        ]
                    )),
                ApplyTimeseriesPredictorStep(
                    output_time_filter=BinaryOperation('>', args=[Identifier('ta.pickup_hour'), Constant(10)]),
                    namespace='mindsdb',
                    predictor=Identifier('tp3', alias=Identifier('tb')),
                    dataframe=Result(1)),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql'],
                          predictor_namespace='mindsdb',
                          predictor_metadata={
                              'tp3': {'timeseries': True,
                                      'order_by_column': 'pickup_hour',
                                      'group_by_columns': ['vendor_id', 'type'],
                                      'window': predictor_window}
                          })

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_join_predictor_timeseries_concrete_date_greater_or_equal(self):
        predictor_window = 10
        group_by_column = 'vendor_id'

        sql = "select * from mysql.data.ny_output as ta left join mindsdb.tp3 as tb where ta.pickup_hour >= 10 and ta.vendor_id = 1"

        query = parse_sql(sql, dialect='mindsdb')

        expected_plan = QueryPlan(
            steps=[
                FetchDataframeStep(integration='mysql',
                                   query=Select(targets=[
                                       Identifier(parts=['ta', group_by_column], alias=Identifier(group_by_column))],
                                       from_table=Identifier('data.ny_output', alias=Identifier('ta')),
                                       where=BinaryOperation('=', args=[Identifier('ta.vendor_id'), Constant(1)]),
                                       distinct=True,
                                   )
                                   ),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=MultipleSteps(
                                  reduce='union',
                                  steps=[
                                      FetchDataframeStep(
                                          integration='mysql',
                                          query=parse_sql(f"SELECT * FROM data.ny_output AS ta\
                                           WHERE ta.pickup_hour < 10 AND ta.vendor_id = 1 AND ta.pickup_hour is not null and\
                                           ta.vendor_id = '$var[vendor_id]' ORDER BY ta.pickup_hour DESC LIMIT {predictor_window}"),
                                      ),
                                      FetchDataframeStep(
                                          integration='mysql',
                                          query=parse_sql("SELECT * FROM data.ny_output AS ta\
                                           WHERE ta.pickup_hour >= 10 AND ta.vendor_id = 1 AND ta.pickup_hour is not null and\
                                           ta.vendor_id = '$var[vendor_id]' ORDER BY ta.pickup_hour DESC"),
                                      ),

                                  ]
                              )),
                ApplyTimeseriesPredictorStep(output_time_filter=BinaryOperation('>=', args=[Identifier('ta.pickup_hour'), Constant(10)]),
                                             namespace='mindsdb',
                                             predictor=Identifier('tp3', alias=Identifier('tb')),
                                             dataframe=Result(1)),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql'],
                          predictor_namespace='mindsdb',
                          predictor_metadata={
                              'tp3': {'timeseries': True,
                                       'order_by_column': 'pickup_hour',
                                       'group_by_columns': [group_by_column],
                                       'window': predictor_window}
                          })

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_join_predictor_timeseries_concrete_date_less(self):
        predictor_window = 10
        group_by_column = 'vendor_id'

        sql = "select * from mysql.data.ny_output as ta join mindsdb.tp3 as tb where ta.pickup_hour < 10 and ta.vendor_id = 1"

        query = parse_sql(sql, dialect='mindsdb')

        expected_plan = QueryPlan(
            steps=[
                FetchDataframeStep(integration='mysql',
                                   query=Select(targets=[
                                       Identifier(parts=['ta', group_by_column], alias=Identifier(group_by_column))],
                                       from_table=Identifier('data.ny_output', alias=Identifier('ta')),
                                       where=BinaryOperation('=', args=[Identifier('ta.vendor_id'), Constant(1)]),
                                       distinct=True,
                                   )
                                   ),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(
                                  integration='mysql',
                                  query=parse_sql("SELECT * FROM data.ny_output AS ta \
                                  WHERE ta.pickup_hour < 10 AND ta.vendor_id = 1 AND ta.pickup_hour is not null and\
                                  ta.vendor_id = '$var[vendor_id]' \
                                  ORDER BY ta.pickup_hour DESC"),
                              ),
                ),
                ApplyTimeseriesPredictorStep(
                    output_time_filter=BinaryOperation('<', args=[Identifier('ta.pickup_hour'), Constant(10)]),
                    namespace='mindsdb',
                    predictor=Identifier('tp3', alias=Identifier('tb')),
                    dataframe=Result(1),
                ),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql'],
                          predictor_namespace='mindsdb',
                          predictor_metadata={
                              'tp3': {'timeseries': True,
                                       'order_by_column': 'pickup_hour',
                                       'group_by_columns': [group_by_column],
                                       'window': predictor_window}
                          })

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_join_predictor_timeseries_concrete_date_less_or_equal(self):
        predictor_window = 10
        group_by_column = 'vendor_id'

        sql = "select * from mysql.data.ny_output as ta left join mindsdb.tp3 as tb where ta.pickup_hour <= 10 and ta.vendor_id = 1"

        query = parse_sql(sql, dialect='mindsdb')

        expected_plan = QueryPlan(
            steps=[
                FetchDataframeStep(integration='mysql',
                                   query=Select(targets=[
                                       Identifier(parts=['ta', group_by_column], alias=Identifier(group_by_column))],
                                       from_table=Identifier('data.ny_output', alias=Identifier('ta')),
                                       where=BinaryOperation('=', args=[Identifier('ta.vendor_id'), Constant(1)]),
                                       distinct=True,
                                   )
                                   ),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(
                                  integration='mysql',
                                  query=parse_sql("SELECT * FROM data.ny_output AS ta\
                                  WHERE  ta.pickup_hour <= 10 AND ta.vendor_id = 1 AND ta.pickup_hour is not null and\
                                   ta.vendor_id = '$var[vendor_id]'\
                                   ORDER BY ta.pickup_hour DESC"),
                              ),
                ),
                ApplyTimeseriesPredictorStep(
                    output_time_filter=BinaryOperation('<=', args=[Identifier('ta.pickup_hour'), Constant(10)]),
                    namespace='mindsdb',
                    predictor=Identifier('tp3', alias=Identifier('tb')),
                    dataframe=Result(1),
                ),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             left=Identifier('result_1'),
                             right=Identifier('result_2'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql'],
                          predictor_namespace='mindsdb',
                          predictor_metadata={
                              'tp3': {'timeseries': True,
                                       'order_by_column': 'pickup_hour',
                                       'group_by_columns': [group_by_column],
                                       'window': predictor_window}
                          })

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]
        

    def test_join_predictor_timeseries_error_on_nested_where(self):
        query = Select(targets=[Identifier('pred.time'), Identifier('pred.price')],
                       from_table=Join(left=Identifier('int.tab1'),
                                       right=Identifier('mindsdb.pred'),
                                       join_type=None,
                                       implicit=True),
                       where=BinaryOperation('and', args=[
                           BinaryOperation('and', args=[BinaryOperation('>', args=[Identifier('tab1.time'), Latest()]),
                                                        BinaryOperation('>', args=[Identifier('tab1.time'), Latest()]),]),
                           BinaryOperation('=', args=[Identifier('tab1.asset'), Constant('bitcoin')]),
                       ]),
                       )

        with pytest.raises(PlanningException):
            plan_query(query,
                       integrations=['int'],
                       predictor_namespace='mindsdb',
                       predictor_metadata={
                           'pred': {'timeseries': True,
                                    'order_by_column': 'time',
                                    'group_by_columns': ['asset'],
                                    'window': 5}
                       })

    def test_join_predictor_timeseries_error_on_invalid_column_in_where(self):
        query = Select(targets=[Identifier('pred.time'), Identifier('pred.price')],
                       from_table=Join(left=Identifier('int.tab1'),
                                       right=Identifier('mindsdb.pred'),
                                       join_type=None,
                                       implicit=True),
                       where=BinaryOperation('and', args=[
                           BinaryOperation('>', args=[Identifier('tab1.time'), Latest()]),
                           BinaryOperation('=', args=[Identifier('tab1.whatver'), Constant(0)]),
                       ]),
                       )

        with pytest.raises(PlanningException):
            plan_query(query,
                       integrations=['int'],
                       predictor_namespace='mindsdb',
                       predictor_metadata={
                           'pred': {'timeseries': True,
                                    'order_by_column': 'time',
                                    'group_by_columns': ['asset'],
                                    'window': 5}
                       })

    def test_join_predictor_timeseries_default_namespace_predictor(self):
        predictor_window = 10
        group_by_column = 'vendor_id'
        query = Select(targets=[Star()],
                       from_table=Join(left=Identifier('tp3', alias=Identifier('tb')),
                                       right=Identifier('mysql.data.ny_output', alias=Identifier('ta')),
                                       join_type=JoinType.LEFT_JOIN),
                       )

        expected_plan = QueryPlan(
            default_namespace='mindsdb',
            steps=[
                FetchDataframeStep(integration='mysql',
                                   query=Select(targets=[Identifier(parts=['ta', group_by_column], alias=Identifier(group_by_column))],
                                                from_table=Identifier('data.ny_output', alias=Identifier('ta')),
                                                distinct=True,
                                                )
                                   ),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(integration='mysql',
                                   query=parse_sql("SELECT * FROM data.ny_output AS ta\
                                    WHERE ta.pickup_hour is not null and ta.vendor_id = '$var[vendor_id]' ORDER BY ta.pickup_hour DESC")
                                   ),
                              ),
                ApplyTimeseriesPredictorStep(
                    namespace='mindsdb',
                    predictor=Identifier('tp3', alias=Identifier('tb')),
                    dataframe=Result(1),
                ),
                JoinStep(left=Result(2),
                         right=Result(1),
                         query=Join(
                             left=Identifier('result_2'),
                             right=Identifier('result_1'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql'],
                          predictor_namespace='mindsdb',
                          default_namespace='mindsdb',
                          predictor_metadata={
                              'tp3': {'timeseries': True,
                                       'order_by_column': 'pickup_hour',
                                       'group_by_columns': [group_by_column],
                                       'window': predictor_window}
                          })

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_join_predictor_timeseries_default_namespace_integration(self):
        predictor_window = 10
        group_by_column = 'vendor_id'
        query = Select(targets=[Star()],
                       from_table=Join(left=Identifier('data.ny_output', alias=Identifier('ta')),
                                       right=Identifier('mindsdb.tp3', alias=Identifier('tb')),
                                       join_type=JoinType.JOIN),
                       )

        expected_plan = QueryPlan(
            default_namespace='mysql',
            steps=[
                FetchDataframeStep(integration='mysql',
                                   query=Select(targets=[Identifier(parts=['ta', group_by_column], alias=Identifier(group_by_column))],
                                                from_table=Identifier('data.ny_output', alias=Identifier('ta')),
                                                distinct=True,
                                                )
                                   ),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(integration='mysql',
                                   query=parse_sql("SELECT * FROM data.ny_output AS ta\
                                    WHERE ta.pickup_hour is not null and ta.vendor_id = '$var[vendor_id]' ORDER BY ta.pickup_hour DESC")
                                   ),
                              ),
                ApplyTimeseriesPredictorStep(
                    namespace='mindsdb',
                    predictor=Identifier('tp3', alias=Identifier('tb')),
                    dataframe=Result(1),
                ),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             left=Identifier('result_1'),
                             right=Identifier('result_2'),
                             join_type=JoinType.JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(query,
                          integrations=['mysql'],
                          predictor_namespace='mindsdb',
                          default_namespace='mysql',
                          predictor_metadata={
                              'tp3': {'timeseries': True,
                                       'order_by_column': 'pickup_hour',
                                       'group_by_columns': [group_by_column],
                                       'window': predictor_window}
                          })

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_timeseries_not_change_query(self):
        sql = "select * from ds.data as ta left join mindsdb.pr as tb where ta.f2 in ('a') and ta.f1 > LATEST"
        query = parse_sql(sql,  dialect='mindsdb')

        query_tree = query.to_tree()

        plan_query(
            query,
            integrations=['ds', 'int'],
            predictor_namespace='mindsdb',
            predictor_metadata={
                'pr': {'timeseries': True, 'window': 3, 'order_by_column': 'f1', 'group_by_columns': ['f2']}},
            default_namespace='mindsdb'
        )

        assert query.to_tree() == query_tree

    def test_timeseries_without_group(self):
        sql = "select * from ds.data.ny_output as ta join mindsdb.pr as tb where ta.f1 > LATEST"
        query = parse_sql(sql,  dialect='mindsdb')

        predictor_window = 3
        expected_plan = QueryPlan(
            default_namespace='ds',
            steps=[
                FetchDataframeStep(
                    integration='ds',
                    query=parse_sql(f"SELECT * FROM data.ny_output AS ta\
                     WHERE ta.f1 is not null\
                     ORDER BY ta.f1 DESC LIMIT {predictor_window}")
                ),
                ApplyTimeseriesPredictorStep(
                    namespace='mindsdb',
                    predictor=Identifier('pr', alias=Identifier('tb')),
                    dataframe=Result(0),
                    output_time_filter=BinaryOperation('>', args=[Identifier('ta.f1'), Latest()]),
                ),
                JoinStep(left=Result(0),
                         right=Result(1),
                         query=Join(
                             left=Identifier('result_0'),
                             right=Identifier('result_1'),
                             join_type=JoinType.JOIN)
                         ),
                ProjectStep(dataframe=Result(2), columns=[Star()]),
            ],
        )

        plan = plan_query(
            query,
            integrations=['ds', 'int'],
            predictor_namespace='mindsdb',
            predictor_metadata={
                'pr': {'timeseries': True, 'window': predictor_window, 'order_by_column': 'f1', 'group_by_columns': []}},
            default_namespace='mindsdb'
        )

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]


    def test_timeseries_with_between_operator(self):
        sql = "select * from ds.data.ny_output as ta \
               left join mindsdb.pr as tb \
               where ta.f2 between '2020-11-01' and '2020-12-01' and ta.f1 > LATEST"

        self._test_timeseries_with_between_operator(sql)

        sql = """select * from (
                    select * from  ds.data.ny_output as ta 
                    where ta.f2 between '2020-11-01' and '2020-12-01' and ta.f1 > LATEST
                )
               left join mindsdb.pr as tb 
               """

        self._test_timeseries_with_between_operator(sql)

    def _test_timeseries_with_between_operator(self, sql):

        query = parse_sql(sql,  dialect='mindsdb')

        predictor_window = 3
        expected_plan = QueryPlan(
            default_namespace='ds',
            steps=[
                FetchDataframeStep(integration='ds',
                                   query=parse_sql("SELECT DISTINCT ta.f2 AS f2 FROM data.ny_output as ta\
                                                    WHERE ta.f2 BETWEEN '2020-11-01' AND '2020-12-01'")),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(
                                  integration='ds',
                                  query=parse_sql(f"SELECT * FROM data.ny_output as ta \
                                                   WHERE ta.f2 BETWEEN '2020-11-01' AND '2020-12-01' \
                                                   AND ta.f1 IS NOT NULL \
                                                   AND ta.f2 = '$var[f2]' \
                                                   ORDER BY ta.f1 DESC LIMIT {predictor_window}")
                              ),
                ),
                ApplyTimeseriesPredictorStep(
                    output_time_filter=BinaryOperation('>', args=[Identifier('ta.f1'), Latest()]),
                    namespace='mindsdb',
                    predictor=Identifier('pr', alias=Identifier('tb')),
                    dataframe=Result(1)),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(
            query,
            integrations=['ds', 'int'],
            predictor_namespace='mindsdb',
            predictor_metadata={
                'pr': {'timeseries': True, 'window': predictor_window, 'order_by_column': 'f1', 'group_by_columns': ['f2']}},
            default_namespace='mindsdb'
        )

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_timeseries_with_multigroup_and_different_case(self):
        sql = "select * from ds.data.ny_output as ta \
               left join mindsdb.pr as tb \
               where ta.f2 > '2020-11-01' and ta.f1 > LATEST"
        query = parse_sql(sql,  dialect='mindsdb')

        predictor_window = 3
        expected_plan = QueryPlan(
            default_namespace='ds',
            steps=[
                FetchDataframeStep(integration='ds',
                                   query=parse_sql("SELECT DISTINCT ta.F2 AS F2, ta.f3 AS f3 FROM data.ny_output as ta\
                                                    WHERE ta.f2 > '2020-11-01'")),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(
                                  integration='ds',
                                  query=parse_sql("SELECT * FROM data.ny_output AS ta\
                                   WHERE ta.f2 > '2020-11-01' AND ta.F1 IS NOT NULL AND ta.F2 = '$var[F2]' AND ta.f3 = '$var[f3]'\
                                   ORDER BY ta.F1 DESC LIMIT 3")
                              ),
                ),
                ApplyTimeseriesPredictorStep(
                    output_time_filter=BinaryOperation('>', args=[Identifier('ta.f1'), Latest()]),
                    namespace='mindsdb',
                    predictor=Identifier('pr', alias=Identifier('tb')),
                    dataframe=Result(1)),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.LEFT_JOIN)
                         ),
                ProjectStep(dataframe=Result(3), columns=[Star()]),
            ],
        )

        plan = plan_query(
            query,
            integrations=['ds', 'int'],
            predictor_namespace='mindsdb',
            predictor_metadata={
                'pr': {'timeseries': True,
                       'window': predictor_window,
                       'order_by_column': 'F1',
                       'group_by_columns': ['F2', 'f3']}},
            default_namespace='mindsdb'
        )

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]


    def test_timeseries_no_group(self):
        predictor_window = 3
        expected_plan = QueryPlan(
            default_namespace='ds',
            steps=[
                MultipleSteps(
                    reduce='union',
                    steps=[
                        FetchDataframeStep(
                            integration='files',
                            query=parse_sql(f"select * from schem.sweat as ta \
                                             WHERE ta.date <= '2015-12-31' AND ta.date IS NOT NULL \
                                             ORDER BY ta.date DESC LIMIT {predictor_window}"),
                        ),
                        FetchDataframeStep(
                            integration='files',
                            query=parse_sql(f"select * from schem.sweat as ta \
                                             WHERE ta.date > '2015-12-31' AND ta.date IS NOT NULL \
                                             ORDER BY ta.date DESC"),
                        ),
                    ]
                ),
                ApplyTimeseriesPredictorStep(
                    output_time_filter=BinaryOperation('>', args=[Identifier('ta.date'), Constant('2015-12-31')]),
                    namespace='mindsdb',
                    predictor=Identifier('tp3', alias=Identifier('tb')),
                    dataframe=Result(0)),
                JoinStep(left=Result(0),
                         right=Result(1),
                         query=Join(
                             right=Identifier('result_1'),
                             left=Identifier('result_0'),
                             join_type=JoinType.JOIN)
                         ),
                ProjectStep(dataframe=Result(2), columns=[Star()]),
            ],
        )

        # different way to join predictor

        sql = '''select * from files.schem.sweat as ta
                  join mindsdb.tp3 as tb 
                 where ta.date > '2015-12-31'
            '''
        self._test_timeseries_no_group(sql, expected_plan)

        sql = '''select * from (
                    select * from files.schem.sweat as ta                  
                    where ta.date > '2015-12-31'
                 )
                 join mindsdb.tp3 as tb 
            '''
        self._test_timeseries_no_group(sql, expected_plan)

        # create table no integration

        sql = '''
            create or replace table files.model_name (
                select * from (
                           select * from schem.sweat as ta                  
                           where ta.date > '2015-12-31'
                )
                join mindsdb.tp3 as tb 
            )       
            '''
        expected_plan2 = copy.deepcopy(expected_plan)
        expected_plan2.add_step(SaveToTable(
            table=Identifier('files.model_name'),
            dataframe=expected_plan2.steps[-1],
            is_replace=True,
        ))
        self._test_timeseries_no_group(sql, expected_plan2)

        # create table with integration

        sql = '''
            create or replace table int1.model_name (
                select * from (
                           select * from files.schem.sweat as ta                  
                           where ta.date > '2015-12-31'
                )
                join mindsdb.tp3 as tb 
            )       
            '''
        expected_plan2 = copy.deepcopy(expected_plan)
        expected_plan2.add_step(SaveToTable(
            table=Identifier('int1.model_name'),
            dataframe=expected_plan2.steps[-1],
            is_replace=True,
        ))
        self._test_timeseries_no_group(sql, expected_plan2)

        # insert into table
        expected_plan2 = copy.deepcopy(expected_plan)
        expected_plan2.add_step(InsertToTable(
            table=Identifier('int1.model_name'),
            dataframe=expected_plan2.steps[-1],
        ))

        sql = '''
            insert into int1.model_name (
                select * from (
                           select * from files.schem.sweat as ta                  
                           where ta.date > '2015-12-31'
                )
                join mindsdb.tp3 as tb 
            )       
            '''
        self._test_timeseries_no_group(sql, expected_plan2)

        sql = '''
            insert into int1.model_name 
            select * from (
                           select * from files.schem.sweat as ta                  
                           where ta.date > '2015-12-31'
                )
                join mindsdb.tp3 as tb 

            '''

        self._test_timeseries_no_group(sql, expected_plan2)

        # update table from select

        expected_plan2 = copy.deepcopy(expected_plan)
        expected_plan2.add_step(UpdateToTable(
            table=Identifier('int1.tbl1'),
            dataframe=expected_plan2.steps[-1],
            update_command=Update(
                table=Identifier('int1.tbl1'),
                update_columns={
                    'a': Identifier('df.a'),
                    'b': Identifier('df.b'),
                },
                where=BinaryOperation(op='=', args=[
                    Identifier('c'),
                    Identifier('df.c')
                ])
            )
        ))

        sql = '''
            update 
                int1.tbl1                   
            set
                a = df.a,
                b = df.b
            from                            
                (
                        select * from (
                                   select * from files.schem.sweat as ta                  
                                   where ta.date > '2015-12-31'
                        )
                        join mindsdb.tp3 as tb 
                )
                as df
            where  
                c = df.c       
        '''
        self._test_timeseries_no_group(sql, expected_plan2)

    def _test_timeseries_no_group(self, sql, expected_plan):
        predictor_window = 3
        query = parse_sql(sql,  dialect='mindsdb')

        plan = plan_query(
            query,
            integrations=['files', 'int1'],
            predictor_namespace='mindsdb',
            predictor_metadata={
                'tp3': {
                    'timeseries': True,
                    'window': predictor_window,
                    'order_by_column': 'date',
                    'group_by_columns': []
                }
            },
            default_namespace='mindsdb'
        )

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_several_groups(self):

        sql = '''
             SELECT tb.saledate as date, tb.MA as forecast
              FROM mindsdb.pr as tb 
              JOIN ds.HR_MA as t
             WHERE t.saledate > LATEST AND t.type = 'house' AND t.bedrooms = 2
             LIMIT 4;
        '''
        predictor_window = 3
        query = parse_sql(sql,  dialect='mindsdb')

        plan = plan_query(
            query,
            integrations=['ds', 'int'],
            predictor_namespace='mindsdb',
            predictor_metadata={
                'pr': {
                    'timeseries': True,
                    'window': predictor_window,
                    'order_by_column': 'saledate',
                    'group_by_columns': ['type', 'bedrooms']}
            },
            default_namespace='mindsdb'
        )

        expected_plan = QueryPlan(
            default_namespace='ds',
            steps=[
                FetchDataframeStep(integration='ds',
                                   query=parse_sql("SELECT DISTINCT t.type AS type, t.bedrooms AS bedrooms FROM HR_MA as t\
                                                    WHERE t.type = 'house' AND t.bedrooms = 2")),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(
                                  integration='ds',
                                  query=parse_sql(f"SELECT * FROM HR_MA as t \
                                                   WHERE t.type = 'house' AND t.bedrooms = 2 \
                                                   AND t.saledate IS NOT NULL \
                                                   AND t.type = '$var[type]' \
                                                   AND t.bedrooms = '$var[bedrooms]' \
                                                   ORDER BY t.saledate DESC LIMIT {predictor_window}")
                              ),
                ),
                ApplyTimeseriesPredictorStep(
                    output_time_filter=BinaryOperation('>', args=[Identifier('t.saledate'), Latest()]),
                    namespace='mindsdb',
                    predictor=Identifier('pr', alias=Identifier('tb')),
                    dataframe=Result(1)),
                JoinStep(left=Result(2),
                         right=Result(1),
                         query=Join(
                             right=Identifier('result_1'),
                             left=Identifier('result_2'),
                             join_type=JoinType.JOIN)
                         ),
                LimitOffsetStep(step_num=4,
                                dataframe=Result(3),
                                limit=Constant(4)),
                ProjectStep(dataframe=Result(4),
                            columns=[Identifier(parts=['tb', 'saledate'], alias=Identifier('date')),
                                     Identifier(parts=['tb', 'MA'], alias=Identifier('forecast'))])
            ],
        )

        for i in range(len(plan.steps)):
            assert plan.steps[i] == expected_plan.steps[i]

    def test_dbt_latest(self):

        sql = '''
          select * from (
             SELECT
               *
             from ds.HR_MA as t
             WHERE t.type = 'house' 
        ) as t1
           JOIN mindsdb.pr as tb                
          WHERE t1.saledate > LATEST 
        '''
        predictor_window = 3
        query = parse_sql(sql,  dialect='mindsdb')

        plan = plan_query(
            query,
            integrations=['ds', 'int'],
            predictor_namespace='mindsdb',
            predictor_metadata={
                'pr': {
                    'timeseries': True,
                    'window': predictor_window,
                    'order_by_column': 'saledate',
                    'group_by_columns': ['type']}
            },
            default_namespace='mindsdb'
        )

        expected_plan = QueryPlan(
            default_namespace='ds',
            steps=[
                FetchDataframeStep(integration='ds',
                                   query=parse_sql("SELECT DISTINCT t.type AS type FROM HR_MA as t\
                                                    WHERE t.type = 'house'")),
                MapReduceStep(values=Result(0),
                              reduce='union',
                              step=FetchDataframeStep(
                                  integration='ds',
                                  query=parse_sql(f"SELECT * FROM HR_MA as t \
                                                   WHERE t.type = 'house' \
                                                   AND t.saledate IS NOT NULL \
                                                   AND t.type = '$var[type]' \
                                                   ORDER BY t.saledate DESC LIMIT {predictor_window}")
                              ),
                ),
                ApplyTimeseriesPredictorStep(
                    output_time_filter=BinaryOperation('>', args=[Identifier('t.saledate'), Latest()]),
                    namespace='mindsdb',
                    predictor=Identifier('pr', alias=Identifier('tb')),
                    dataframe=Result(1)),
                JoinStep(left=Result(1),
                         right=Result(2),
                         query=Join(
                             right=Identifier('result_2'),
                             left=Identifier('result_1'),
                             join_type=JoinType.JOIN)
                         ),
                ProjectStep(dataframe=Result(3),
                            columns=[Star()])
            ],
        )

        for i in range(len(plan.steps)):
            # print(plan.steps[i])
            # print(expected_plan.steps[i])
            assert plan.steps[i] == expected_plan.steps[i]