import re # для работы с регулярными выражениями (для поиска и обработки строк в файле)
import argparse # для обработки аргументов командной строки
import toml # библиотека для работы с форматом TOML


# Исключение для синтаксических ошибок
class SyntaxError(Exception):
    pass


'''
класс отвечает за разбор и преобразование конфигурационного файла
'''
class ConfigParser:
    def __init__(self):
        self.constants = {} # будут храниться объявленные константы и их значения

    '''Разбор входного текста'''
    def parse(self, input_text):
        lines = input_text.strip().splitlines() # удаляет пустые строки в начале и конце, затем разбивает текст на строки
        parsed_data = {} # словарь, куда будут записываться обработанные данные
        current_dict = None # временный словарь для хранения пар ключ-значение, когда мы находим блок @{ ... }

        for line in lines:
            line = line.strip() # удаляет пробелы в начале и конце строки
            if not line or line.startswith("#"):
                continue  # Если строка пустая (not line) или начинается с комментария (#), мы пропускаем её

            if line.startswith("def "): # Если строка начинается с def, это определение константы
                self._parse_constant(line)
            elif line.startswith("@{"): # Если строка начинается с @{, мы создаем новый словарь current_dict для хранения его содержимого
                if current_dict is not None:
                    raise SyntaxError("Nested dictionaries are not allowed.")
                current_dict = {}
            elif line.startswith("}") and current_dict is not None:
                dict_name = self._generate_dict_name(parsed_data) # придумываем уникальное имя для этого словаря
                parsed_data[dict_name] = current_dict # Добавляем его в parsed_data
                current_dict = None # сбрасываем current_dict в None
            elif current_dict is not None: # Если мы находимся внутри словаря, обрабатываем строку как пару ключ=значение с помощью _parse_key_value
                key, value = self._parse_key_value(line)
                current_dict[key] = value
            else:
                raise SyntaxError(f"Unexpected line: {line}")

        return parsed_data


    '''Обработка констант'''
    def _parse_constant(self, line):
        # Регулярное выражение ищет строки вида def имя := значение
        match = re.match(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:=\s*(.+)", line)
        if not match:
            raise SyntaxError(f"Invalid constant definition: {line}")

        name, value_expr = match.groups() # Извлекаем name (имя константы) и value_expr (выражение)
        value_expr = value_expr.replace("\n", " ")  # Удаляем переносы строк
        value = self._evaluate_expression(value_expr.strip()) # Вычисляем значение
        self.constants[name] = value # Сохраняем результат в self.constants


    '''Вычисление выражений'''
    def _evaluate_expression(self, expr):
        if expr.isdigit(): # Если выражение — это число, возвращаем его как int
            return int(expr)

        # Обрабатывается выражение chr(n), которое преобразует число в символ
        if expr.startswith("chr(") and expr.endswith(")"):
            inner = expr[4:-1]
            return chr(int(inner))

        # Ищем выражения в формате #(операция левый_операнд правый_операнд)
        match = re.match(r"#\(([-+*/])\s*(\S+)\s*(\S+)\)", expr)
        if match:
            op, left, right = match.groups() # Извлекаем операнды и оператор
            # Вычисляем значения операндов
            left_val = self._get_value_from_expression(left)
            right_val = self._get_value_from_expression(right)

            # Применяем соответствующую арифметическую операцию
            if op == "+":
                return left_val + right_val
            elif op == "-":
                return left_val - right_val
            elif op == "*":
                return left_val * right_val
            elif op == "/":
                return left_val / right_val
            else:
                raise SyntaxError(f"Unsupported operation: {op}")

        match = re.match(r"#\(([-+*/])\s*(.+)\)", expr) # # Обрабатываем выражения с одним операндом, например #(- 5)
        if match:
            op, inner_expr = match.groups() # Извлекаем оператор и выражение
            inner_value = self._evaluate_expression(inner_expr) # Рекурсивно вычисляем внутреннее выражение
            if op == "+":  # Если оператор "+", результат равен самому значению.
                return inner_value
            elif op == "-":  # Если "-", возвращаем отрицательное значение.
                return -inner_value
            elif op == "*":  # Если "*", результат равен самому значению.
                return inner_value
            elif op == "/":  # Если "/", возвращаем обратное значение (1/значение).
                return 1 / inner_value
            else:
                raise SyntaxError(f"Unsupported operation: {op}")  # Если оператор неизвестен, выбрасываем ошибку.

        raise SyntaxError(f"Invalid expression: {expr}")


    '''извлекать значения операндов'''

    def _get_value_from_expression(self, value):
        if value.isdigit():  # Если значение — это число
            return int(value)  # Преобразуем в `int` и возвращаем
        elif value in self.constants: # Если значение — это имя константы
            return self.constants[value] # Возвращаем значение из словаря констант
        else:
            raise SyntaxError(f"Unknown variable or value: {value}")


    '''Обработка пар ключ-значение'''
    def _parse_key_value(self, line):
        # Регулярное выражение ищет пары ключ = значение;
        match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*) = (.+);", line)
        if not match:
            raise SyntaxError(f"Invalid key-value pair: {line}")

        key, value = match.groups() # Извлекаем ключ и значение
        value = self._parse_value(value) # преобразуем значение
        return key, value


    '''обрабатывает значение пары ключ=значение'''
    def _parse_value(self, value):
        # Обрабатываем числа, строки в [[...]], ссылки на константы
        if value.isdigit(): # Если значение — это число
            return int(value) # Преобразуем в `int`
        if re.match(r"^\d+\.\d+$", value): # Если значение — это число с плавающей точкой
            return float(value) # Преобразуем в `float`
        if value.startswith("[[") and value.endswith("]]"): # Если значение в двойных квадратных скобках
            return value[2:-2]  # Убираем скобки и возвращаем строку
        if value in self.constants: # Если значение — это имя константы
            return self.constants[value] # Возвращаем значение константы
        raise SyntaxError(f"Invalid value: {value}")


    '''генерирует уникальные имена для словарей'''
    def _generate_dict_name(self, parsed_data):
        index = 1
        while f"dict{index}" in parsed_data: # Проверяем, занято ли имя `dict1`, `dict2` и т.д.
            index += 1
        return f"dict{index}" # Возвращаем свободное имя



def main():
    '''Создаем обработчик аргументов командной строки. Ожидаем один аргумент — путь к входному файлу'''
    parser = argparse.ArgumentParser(description="Convert configuration file to TOML format.")
    parser.add_argument("input_file", help="Path to the input file.")
    args = parser.parse_args()

    try:
        with open(args.input_file, "r", encoding="utf-8") as file: # Открываем файл
            input_text = file.read() # Читаем его содержимое

        config_parser = ConfigParser() # Создаем объект `ConfigParser`
        parsed_data = config_parser.parse(input_text) # Разбираем входной текст

        toml_output = toml.dumps(parsed_data) # Преобразуем результат в TOML

        print(f"\n{toml_output}")

    except SyntaxError as e: # Обработка синтаксических ошибок
        print(f"Syntax Error: {e}")
    except FileNotFoundError: # Если файл не найден
        print("Error: Input file not found.")
    except Exception as e: # Любые другие ошибки
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
