



def test_file(file):
    import os
    if os.path.exists(file):
        if os.path.isfile(file):
            return True
        else:
            assert(False)
    else:
        return False


def read_file(file):
    assert(isinstance(file, str))
    with open(file, "rb") as f:
        bytes_data = f.read()
    return bytes_data


def write_file(file, bytes_data):
    assert(isinstance(file, str))
    with open(file, 'wb') as f:
        f.write(bytes_data)
    return


def get_url(url):
    import requests
    http_answer = requests.get(url, timeout=(5, 10))
    if http_answer.status_code != 200:
        return None
    bytes_data = http_answer.content
    return bytes_data


def get_utc():
    import datetime
    Time_UTC = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    return Time_UTC


def get_file_modif_time(file):
    import os
    import datetime
    assert(test_file(file) is True)
    modTimesinceEpoc = os.path.getmtime(file)
    modif_date = datetime.datetime.utcfromtimestamp(modTimesinceEpoc).replace(tzinfo=datetime.timezone.utc).replace(microsecond=0)
    return modif_date


def compute_age(date):
    if type(date) is str:
        import datetime
        date = datetime.datetime.fromisoformat(date)
    return round((get_utc() - date).total_seconds())


def get_file_age(file):
    modif_date = get_file_modif_time(file)
    return compute_age(modif_date)


