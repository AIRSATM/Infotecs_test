import requests
import time
import pytest
import subprocess

path = "webcalculator.exe"
host = "127.0.0.1"
port = 17678
a_port = 17679

base_url = f"http://{host}:{port}/api"
alt_url = f"http://{host}:{a_port}/api"

x, y = 42, 24

def start(start_host = host, start_port = port):
    proc = subprocess.Popen(
        [path, "start", str(start_host), str(start_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)
    return proc

def stop():
    subprocess.run([path, "stop"], capture_output=True)
    time.sleep(1)

def alive(b_url=base_url) -> bool:
    try:
        r = requests.get(f"{base_url}/state",timeout=3)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False
    
@pytest.fixture(scope="module", autouse=True)
def app():
    start()
    yield
    stop()

class TestResponse:
    def test_state_returns_correct_keys(self):
        r = requests.get(f"{base_url}/state")
        assert r.status_code == 200
        body = r.json()
        assert "statusCode" in body
        assert "state" in body

    def test_state_returns_ok(self):
        r = requests.get(f"{base_url}/state")
        body = r.json()
        assert body["statusCode"] == 0
        assert body["state"].replace("О", "O").replace("К", "K").upper() == "OK"

    def test_arithmetic_response_has_status_code_and_result(self):
        r = requests.post(f"{base_url}/addition", json={"x": x, "y": y})
        assert r.status_code == 200
        body = r.json()
        assert "statusCode" in body
        assert "result" in body

    def test_arithmetic_status_code_is_zero_on_success(self):
        r = requests.post(f"{base_url}/addition", json={"x": x, "y": y})
        assert r.json()["statusCode"] == 0

    def test_result_is_integer(self):
        r = requests.post(f"{base_url}/addition", json={"x": x, "y": y})
        result = r.json()["result"]
        assert isinstance(result, int), f"result должен быть int, получили {type(result)}"

    def test_content_type_is_json(self):
        r = requests.post(f"{base_url}/addition", json={"x": x, "y": y})
        assert "application/json" in r.headers.get("Content-Type", "")

    def test_options_request_is_allowed(self):
        r = requests.options(f"{base_url}/addition")
        assert r.status_code not in (404, 500)

    def test_get_request_to_arithmetic_endpoint(self):
        r = requests.get(f"{base_url}/addition")
        assert r.status_code != 404

class TestArithmetic:
    def test_addition_basic(self):
        r = requests.post(f"{base_url}/addition", json={"x": 42, "y": 24})
        assert r.json()["result"] == 66

    def test_addition_negative_numbers(self):
        r = requests.post(f"{base_url}/addition", json={"x": -10, "y": -5})
        assert r.json()["result"] == -15

    def test_addition_with_zero(self):
        r = requests.post(f"{base_url}/addition", json={"x": 0, "y": 0})
        assert r.json()["result"] == 0

    def test_addition_mixed_signs(self):
        r = requests.post(f"{base_url}/addition", json={"x": 100, "y": -50})
        assert r.json()["result"] == 50

    def test_multiplication_basic(self):
        r = requests.post(f"{base_url}/multiplication", json={"x": 42, "y": 24})
        assert r.json()["result"] == 1008

    def test_multiplication_by_zero(self):
        r = requests.post(f"{base_url}/multiplication", json={"x": 999, "y": 0})
        assert r.json()["result"] == 0

    def test_multiplication_negative(self):
        r = requests.post(f"{base_url}/multiplication", json={"x": -3, "y": 4})
        assert r.json()["result"] == -12

    def test_multiplication_both_negative(self):
        r = requests.post(f"{base_url}/multiplication", json={"x": -5, "y": -5})
        assert r.json()["result"] == 25

    def test_division_basic(self):
        r = requests.post(f"{base_url}/division", json={"x": 42, "y": 24})
        assert r.json()["result"] == 1

    def test_division_exact(self):
        r = requests.post(f"{base_url}/division", json={"x": 100, "y": 10})
        assert r.json()["result"] == 10

    def test_division_negative(self):
        r = requests.post(f"{base_url}/division", json={"x": -10, "y": 3})
        assert r.json()["result"] in (-4, -3)

    def test_remainder_basic(self):
        r = requests.post(f"{base_url}/remainder", json={"x": 42, "y": 24})
        assert r.json()["result"] == 18

    def test_remainder_exact_division(self):
        r = requests.post(f"{base_url}/remainder", json={"x": 10, "y": 5})
        assert r.json()["result"] == 0

    def test_remainder_larger_divisor(self):
        r = requests.post(f"{base_url}/remainder", json={"x": 3, "y": 10})
        assert r.json()["result"] == 3

    def test_addition_max_int32_values(self):
        max_int32 = 2_147_483_647
        r = requests.post(f"{base_url}/addition", json={"x": max_int32, "y": 0})
        assert r.status_code == 200
        assert "statusCode" in r.json()

    def test_addition_min_int32_values(self):
        min_int32 = -2_147_483_648
        r = requests.post(f"{base_url}/addition", json={"x": min_int32, "y": 0})
        assert r.status_code == 200
        assert "statusCode" in r.json()

class TestManagement:
    def test_stop_command(self):
        stop()
        time.sleep(1)
        assert not alive()
        start()

    def test_restart_command(self):
        result = subprocess.run(
            [path, "restart"], capture_output=True, text=True
        )
        time.sleep(2)
        assert alive()

    def test_host_and_port(self):
        stop()
        subprocess.Popen([path, "start"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)
        assert alive(base_url)

    def test_custom_port(self):
        stop()
        
        is_alive = False

        proc = subprocess.Popen(
            [path, "start", host, str(a_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        time.sleep(4)
        
        exit_code = proc.poll()
        if exit_code is not None:
            stdout, stderr = proc.communicate()
            pytest.fail(
                f"Процесс завершился сразу с кодом {exit_code}\n"
                f"stdout: {stdout.decode()}\n"
                f"stderr: {stderr.decode()}"
            )
        else:
            is_alive = alive(alt_url)
        
        stop()
        start()
        
        assert alive, f"Сервер не доступен на порту {a_port}"

    def test_default_port_when_only_host_given(self):
        stop()
        subprocess.Popen(
            [path, "start", host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(2)
        assert alive(base_url)

    def test_show_log_does_not_crash(self):
        result = subprocess.run(
            [path, "show_log"], capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0 or len(result.stdout) > 0

    def test_help_flag(self):
        result = subprocess.run(
            [path, "--help"], capture_output=True, text=True, timeout=5
        )
        output = result.stdout + result.stderr
        assert len(output) > 0

    def test_restart_preserves_address(self):
        assert alive(base_url)
        subprocess.run([path, "restart"], capture_output=True)
        time.sleep(2)
        assert alive(base_url)

class TestNegative:
    def test_missing_key_x(self):
        r = requests.post(f"{base_url}/addition", json={"y": 10})
        body = r.json()
        assert body["statusCode"] == 2
        assert "statusMessage" in body

    def test_missing_key_y(self):
        r = requests.post(f"{base_url}/addition", json={"x": 10})
        body = r.json()
        assert body["statusCode"] == 2

    def test_empty_body(self):
        r = requests.post(f"{base_url}/addition", json={})
        body = r.json()
        assert body["statusCode"] in (2, 5)

    def test_string_value_instead_of_int(self):
        r = requests.post(f"{base_url}/addition", json={"x": "abc", "y": 10})
        body = r.json()
        assert body["statusCode"] == 3, "Строковое значение должно дать код ошибки 3"

    def test_float_value_instead_of_int(self):
        r = requests.post(f"{base_url}/addition", json={"x": 3.14, "y": 10})
        body = r.json()
        assert body["statusCode"] == 3, "Float-значение должно дать код ошибки 3"

    def test_value_exceeds_int32(self):
        too_big = 2_147_483_648  # max_int32 + 1
        r = requests.post(f"{base_url}/addition", json={"x": too_big, "y": 0})
        body = r.json()
        assert body["statusCode"] == 4, "Превышение int32 должно дать код ошибки 4"

    def test_division_by_zero(self):
        r = requests.post(f"{base_url}/division", json={"x": 10, "y": 0})
        body = r.json()
        assert body["statusCode"] == 1, "Деление на 0 должно дать код ошибки 1"

    def test_remainder_by_zero(self):
        r = requests.post(f"{base_url}/remainder", json={"x": 10, "y": 0})
        body = r.json()
        assert body["statusCode"] == 1

    def test_invalid_json_body(self):
        r = requests.post(
            f"{base_url}/addition",
            data="это не json",
            headers={"Content-Type": "application/json"},
        )
        body = r.json()
        assert body["statusCode"] == 5

    def test_unknown_endpoint_returns_error(self):
        r = requests.post(f"{base_url}/nonexistent", json={"x": 1, "y": 2})
        assert r.status_code in (404, 400, 200) 
        assert r.status_code != 500

    def test_error_response_has_status_message(self):
        
        r = requests.post(f"{base_url}/addition", json={"y": 10})  # нет x
        body = r.json()
        assert "statusMessage" in body
        assert isinstance(body["statusMessage"], str)
        assert len(body["statusMessage"]) > 0