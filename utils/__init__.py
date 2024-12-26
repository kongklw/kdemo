from datetime import datetime


def convert_string_datetime(string):
    return datetime.strptime(string, '%Y-%m-%dT%H:%M:%S')


def convert_seconds(seconds):
    hours = seconds // 3600
    min = (seconds % 3600) // 60
    sec = seconds % 60

    return "{}h {}m {}s".format(hours, min, sec)
