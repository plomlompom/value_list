import fileinput
lines = []
for line in fileinput.input():
    lines += [line]

value_lines = []
indentations = [""]
depth = 0
for index in range(len(lines)):
    line = lines[index]
    if line[-1] == "\n":
        line = line[:-1]
    indentation = ""
    empty = True
    for i in range(len(line)):
        char = line[i]
        if char in " \t":
            indentation = indentation + char
        elif char in "*-+" and len(line) > i+2 and line[i+1] == " ":
            indentation = indentation + char + " "
            i = i + 1
            empty = False
            break
        else:
            empty = False
            break
    if empty:
        value_lines.append({"index": index + 1, "indent": indentation,
                            "value": "empty"})
        continue
    content = line[i:]
    if indentation in indentations:
        if indentation != indentations[-1]:
            depth = indentations.index(indentation)
            indentations = indentations[:depth + 1]
    else:
        indentations.append(indentation)
        depth = depth + 1
    content = content.split(None, 1)
    value = "empty"
    currency = ""
    if len(content) > 0:
        value_and_currency = content[0]
        if "?" == value_and_currency[0]:
            value = "?"
            currency = value_and_currency[1:]
        else:
            i = int(value_and_currency[0] in "+-")
            while i < len(value_and_currency):
                if value_and_currency[i] not in "0123456789.":
                    break
                i = i + 1
            value = value_and_currency[:i]
            currency = value_and_currency[i:]
    description = ""
    if len(content) > 1:
        description = content[1]
    value_lines.append({"index": index + 1, "depth": depth,
                        "indent": indentation, "value": value,
                        "currency": currency, "description": description,
                        "contains": []})


def build_subpackage(i, limit):
    last_depth = value_lines[i]["depth"]
    package = []
    while i >= 0 and last_depth > limit:
        x = value_lines[i]
        if x["value"] == "empty" or x["depth"] == last_depth:
            package.append(x)
        elif x["depth"] == last_depth - 1:
            package.reverse()
            x["contains"] = package
            last_depth = x["depth"]
            package = [x]
        else:
            i, sub_package = build_subpackage(i, last_depth)
            i = i + 1
            package = package + sub_package
        i = i - 1
    package.reverse()
    return i, package


start_i = len(value_lines) - 1
limit = -1
i, hierarchy = build_subpackage(start_i, limit)


def calc_values(package, errors):
    import decimal
    c = decimal.getcontext()
    c.traps[decimal.Inexact] = True

    def err(errors, x, correct, category):
        errors += ["ERROR: line " + str(x["index"]) + " – " + category +
                   " should be " + str(correct) + " but is " +
                   str(x[category])]

    def form(n):
        return decimal.Decimal(n).quantize(decimal.Decimal('0.01'))
    total = form(0)
    first = True
    legal_currency = ""
    for x in package:
        if "empty" == x["value"]:
            continue
        elif first:
            legal_currency = x["currency"]
            first = False
        if x["currency"] != legal_currency:
            err(errors, x, legal_currency, "currency")
        value = False
        currency = False
        if len(x["contains"]) > 0:
            value, currency, errors = calc_values(x["contains"], errors)
            if currency != legal_currency:
                err(errors, x, currency, "currency")
            if "?" == x["value"]:
                x["value"] = value
            elif form(x["value"]) != value:
                err(errors, x, value, "value")
                x["value"] = form(x["value"])
            else:
                x["value"] = value
        elif "?" == x["value"]:
            errors += ["ERROR: line " + str(x["index"]) +
                       " – can't resolve '?'"]
            continue
        else:
            x["value"] = form(x["value"])
        total = total + form(x["value"])
    return total, legal_currency, errors


_, _, errors = calc_values(hierarchy, [])


def print_value_list(package):
    import decimal
    for x in package:
        if x["value"] == "empty":
            print(x["indent"])
            continue
        str_val = "?"
        if isinstance(x["value"], decimal.Decimal):
            if x["value"] < 0:
                str_val = str(x["value"])
            else:
                str_val = "+" + str(x["value"])
        print(x["indent"] + str_val + x["currency"] + " " + x["description"])
        if len(x["contains"]) > 0:
            print_value_list(x["contains"])


print_value_list(hierarchy)
for err in errors:
    print(err)
