# -*- coding: utf-8 -*-
import datetime
import json
import unittest

from bvggrabber.api import QueryApi, Departure, Response, compute_remaining
from bvggrabber.utils.format import fullformat


class TestFunctions(unittest.TestCase):

    def test_compute_remaining(self):
        dates = [datetime.datetime(2013, 1, 2, 3, 4, 0),
                 datetime.datetime(2013, 1, 2, 3, 4, 1),
                 datetime.datetime(2013, 1, 2, 3, 4, 59),
                 datetime.datetime(2013, 1, 2, 3, 5, 0),
                 datetime.datetime(2013, 1, 2, 3, 5, 1),
                 datetime.datetime(2013, 1, 2, 3, 5, 59)]

        target = [[0, 0, 0, 60, 60, 60],
                  [-60, 0, 0, 0, 60, 60],
                  [-60, -60, 0, 0, 0, 60],
                  [-60, -60, -60, 0, 0, 0],
                  [-120, -60, -60, -60, 0, 0],
                  [-120, -120, -60, -60, -60, 0]]
        for start in range(len(dates)):
            for end in range(len(dates)):
                s = dates[start]
                e = dates[end]
                t = target[start][end]
                self.assertEqual(compute_remaining(s, e),
                                 target[start][end],
                                 "Start: %s; End: %s; target: %d" % (
                                     fullformat(s), fullformat(e), t))

    def test_compute_remaining_error(self):
        self.assertRaises(TypeError, compute_remaining,
                          1357092240, datetime.datetime(2013, 1, 2, 3, 4, 1))
        self.assertRaises(TypeError, compute_remaining,
                          datetime.datetime(2013, 1, 2, 3, 4, 0), 1357092241)
        self.assertRaises(TypeError, compute_remaining,
                          1357092240, 1357092241)


class TestResponse(unittest.TestCase):

    def test_init_ambiguous(self):
        response = Response(False, ['s1', 's2'])
        self.assertFalse(response.state)
        self.assertEqual(str(response.error), "Station is ambiguous: s1, s2")

    def test_init_not_found(self):
        response = Response(False)
        self.assertFalse(response.state)
        self.assertEqual(str(response.error), "Station does not exist")

    def test_init_error_string(self):
        response = Response(False, error="An error occurred")
        self.assertFalse(response.state)
        self.assertEqual(str(response.error), "An error occurred")

    def test_merge(self):
        departures = [Departure("ERP", "HBF",
                                datetime.datetime(2013, 1, 2, 3, 4, 1), "U2"),
                      Departure("HBF", "ERP",
                                datetime.datetime(2013, 2, 1, 3, 4, 1), "U55")]
        departures2 = [Departure("ERP", "HBF",
                                 datetime.datetime(2013, 1, 2, 3, 4, 1), "U6"),
                       Departure("HBF", "ERP",
                                 datetime.datetime(2013, 2, 1, 3, 4, 1), "U9")]
        allDepartures = [("Marchbrücke", departures),
                         ("S Tiergarten", departures2)]
        r1 = Response(True, "Marchbrücke", departures)
        r2 = Response(True, "S Tiergarten", departures2)
        r3 = Response(False, [])
        self.assertRaises(ValueError, r1.merge, r3)
        self.assertRaises(ValueError, r3.merge, r2)
        self.assertRaises(TypeError, r1.merge, departures)
        r1.merge(r2)
        self.assertEqual(r1.departures, allDepartures)

    def test_json_success(self):
        since = datetime.datetime(2013, 1, 2, 3, 0, 0)
        departures = [Departure("ZOO", "HBF",
                                datetime.datetime(2013, 1, 2, 3, 4, 0), "S5",
                                since=since),
                      Departure("ZOO", "ERP",
                                datetime.datetime(2013, 1, 2, 3, 5, 0), "U2",
                                since=since)]
        json1 = [['ZOO', [{
                'start': 'ZOO',
                'line': 'S5',
                'end': 'HBF',
                'remaining': 240, 
            }, {
                'start': 'ZOO',
                'line': 'U2',
                'end': 'ERP',
                'remaining': 300, 
            },
        ]]]
        response = Response(True, "ZOO", departures)
        self.assertEqual(json.loads(response.json), json1)

    def test_json_failure(self):
        response = Response(False, ['ERP', 'ZOO'])
        self.assertEqual(response.json, json.dumps("Station is ambiguous: ERP, ZOO"))

    def test_departures_failure(self):
        response = Response(False, ['ERP', 'ZOO'])
        self.assertEqual(response.departures, "Station is ambiguous: ERP, ZOO")


class TestQueryApi(unittest.TestCase):

    def test_call(self):
        q = QueryApi()
        self.assertRaises(NotImplementedError, q.call)


class BaseTestDeparture(unittest.TestCase):

    def setUp(self):
        self.since = datetime.datetime(2013, 1, 2, 3, 4, 0)
        self.delta1 = datetime.timedelta(seconds=45)
        self.delta2 = datetime.timedelta(seconds=80)
        self.delta3 = datetime.timedelta(seconds=150)


class TestDepartureTimestamp(BaseTestDeparture):

    def setUp(self):
        super(TestDepartureTimestamp, self).setUp()
        self.sincets = 1357092240
        self.since = datetime.datetime.fromtimestamp(self.sincets)
        self.delta1 = self.delta1.total_seconds()
        self.delta2 = self.delta2.total_seconds()
        self.delta3 = self.delta3.total_seconds()

    def test_timestamp_futur(self):
        when = self.sincets + self.delta1
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, 0)

        when = self.sincets + self.delta2
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, 60)

        when = self.sincets + self.delta3
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, 120)

    def test_timestamp_now(self):
        when = self.sincets
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, 0)

    def test_timestamp_past(self):
        when = self.sincets - self.delta1
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, -60)

        when = self.sincets - self.delta2
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, -120)

        when = self.sincets - self.delta3
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, -180)


class TestDepartureString(BaseTestDeparture):

    def test_string_futur(self):
        when = fullformat(self.since + self.delta1)
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, 0)

        when = fullformat(self.since + self.delta2)
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, 60)

        when = fullformat(self.since + self.delta3)
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, 120)

    def test_string_now(self):
        when = fullformat(self.since)
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, 0)

    def test_string_past(self):
        when = fullformat(self.since - self.delta1)
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, -60)

        when = fullformat(self.since - self.delta2)
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, -120)

        when = fullformat(self.since - self.delta3)
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, -180)


class TestDepartureDatetime(BaseTestDeparture):

    def test_datetime_futur(self):
        when = self.since + self.delta1
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, 0)

        when = self.since + self.delta2
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, 60)

        when = self.since + self.delta3
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, 120)

    def test_datetime_now(self):
        when = self.since
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, 0)

    def test_datetime_past(self):
        when = self.since - self.delta1
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, -60)

        when = self.since - self.delta2
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, -120)

        when = self.since - self.delta3
        dep = Departure("from", "to", when, "line", since=self.since)
        self.assertEqual(dep.remaining, -180)


class TestDeparture(BaseTestDeparture):

    def test_error(self):
        self.assertRaises(TypeError, Departure, "from", "to", ["when"], "line")
        self.assertIsInstance(Departure("from", "to", "16:15\n \t*", "line"),
                              Departure)

    def test_regression_new_day(self):
        now = datetime.datetime(2013, 1, 2, 23, 59, 0)

        dep = datetime.datetime(2013, 1, 2, 0, 1, 2)
        departure = Departure("From My Station", "To Your Station", dep,
                              "A Line", since=now)
        self.assertEqual(departure.remaining, 120)
        departure = Departure("From My Station", "To Your Station", dep,
                              "A Line", since=now, no_add_day=True)
        self.assertEqual(departure.remaining, -86280)

        mitday_current_day = datetime.datetime(2013, 1, 2, 11, 59, 0)
        departure = Departure("From My Station", "To Your Station",
                              mitday_current_day, "A Line", since=now)
        self.assertEqual(departure.remaining, -43200)
        departure = Departure("From My Station", "To Your Station",
                              mitday_current_day, "A Line", since=now,
                              no_add_day=True)

        mitday_next_day = datetime.datetime(2013, 1, 2, 11, 58, 59)
        departure = Departure("From My Station", "To Your Station",
                              mitday_next_day, "A Line", since=now)
        self.assertEqual(departure.remaining, 43140)
        departure = Departure("From My Station", "To Your Station",
                              mitday_next_day, "A Line", since=now,
                              no_add_day=True)
        self.assertEqual(departure.remaining, -43260)

    def test_str(self):
        now = datetime.datetime(2013, 1, 2, 12, 13, 0)
        dep = datetime.datetime(2013, 1, 2, 12, 15, 0)
        departure = Departure("From My Station", "To Your Station", dep,
                              "A Line", since=now)
        string = 'Start: From My Station, End: To Your Station, when: 12:15, now: 12:13, line: A Line'
        self.assertEqual(str(departure), string)
        self.assertEqual(repr(departure), string)


class TestDepartureTotalOrder(unittest.TestCase):

    def setUp(self):
        self.td = datetime.timedelta(minutes=1)

        self.dt_now1 = datetime.datetime(2013, 1, 2, 3, 4, 1)
        self.dt_now2 = datetime.datetime(2013, 1, 2, 3, 4, 1)
        self.dt_earlier = datetime.datetime(2013, 1, 2, 3, 4, 1) - self.td
        self.dt_later = datetime.datetime(2013, 1, 2, 3, 4, 1) + self.td

    def test_equal(self):
        self.assertEqual(self.dt_now1, self.dt_now2)

    def test_less(self):
        self.assertLess(self.dt_earlier, self.dt_now1)
        self.assertLess(self.dt_earlier, self.dt_later)
        self.assertLess(self.dt_now1, self.dt_later)

    def test_greater(self):
        self.assertGreater(self.dt_now1, self.dt_earlier)
        self.assertGreater(self.dt_later, self.dt_earlier)
        self.assertGreater(self.dt_later, self.dt_now1)

    def test_not_equal(self):
        self.assertNotEqual(self.dt_now1, self.dt_earlier)
        self.assertNotEqual(self.dt_now1, self.dt_later)
        self.assertNotEqual(self.dt_now2, self.dt_earlier)
        self.assertNotEqual(self.dt_now2, self.dt_later)
        self.assertNotEqual(self.dt_earlier, self.dt_later)

    def test_sorting_single(self):
        l = [self.dt_now1, self.dt_later, self.dt_earlier]
        self.assertEqual([self.dt_earlier, self.dt_now1, self.dt_later],
                         sorted(l))
        self.assertEqual([self.dt_later, self.dt_now1, self.dt_earlier],
                         sorted(l, reverse=True))

    def test_sorting_multiple(self):
        l = [self.dt_now1, self.dt_earlier, self.dt_later,
             self.dt_now2, self.dt_later, self.dt_earlier,
             self.dt_earlier, self.dt_later, self.dt_now2]
        self.assertEqual([self.dt_earlier, self.dt_earlier, self.dt_earlier,
                          self.dt_now1, self.dt_now2, self.dt_now2,
                          self.dt_later, self.dt_later, self.dt_later],
                         sorted(l))
        self.assertEqual([self.dt_later, self.dt_later, self.dt_later,
                          self.dt_now1, self.dt_now2, self.dt_now2,
                          self.dt_earlier, self.dt_earlier, self.dt_earlier],
                         sorted(l, reverse=True))
