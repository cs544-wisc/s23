import os, sys, json, csv, re, math
import matplotlib.pyplot as plt
from collections import namedtuple

Answer = namedtuple("Answer", ["question", "type", "value", "notes"])

def read_code_cells(ipynb, default_notes={}):
    answers = []
    with open(ipynb) as f:
        nb = json.load(f)
        cells = nb["cells"]
        expected_exec_count = 1
        for cell in cells:
            if "execution_count" in cell and cell["execution_count"]:
                exec_count = cell["execution_count"]
                if exec_count != expected_exec_count:
                    raise Exception(f"Expected execution count {expected_exec_count} but found {exec_count}. Please do Restart & Run all then save before running the tester.")
                expected_exec_count = exec_count + 1
            if cell["cell_type"] != "code":
                continue
            if not cell["source"]:
                continue
            m = re.match(r"#[qQ](\d+)(.*)", cell["source"][0].strip())
            if not m:
                continue
            qnum = int(m.group(1))
            notes = m.group(2).strip()
            config = parse_question_config(notes)
            if "run" in config:
                exec(config["run"])
            print(f"Reading Question {qnum}")
            if qnum in [a.question for a in answers]:
                raise Exception(f"Answer {qnum} repeated!")
            expected = max([0] + [a.question for a in answers]) + 1
            if qnum != expected:
                print(f"Warning: Expected question {expected} next but found {qnum}!")

            # plots are display_data, so try to find those before looking for regular cell outputs
            outputs = [o for o in cell["outputs"]
                       if o.get("output_type") == "display_data"]
            if len(outputs) == 0:
                outputs = [o for o in cell["outputs"]
                           if o.get("output_type") == "execute_result"]
            assert len(outputs) < 2
            if len(outputs) > 0:
                output_str = "".join(outputs[0]["data"]["text/plain"]).strip()
                if output_str.startswith("<Figure"):
                    output_str = "plt.Figure()"
                if output_str == "nan":
                    output_str = 'float("nan")'
            else:
                output_str = "None"
            try:
                output = eval(output_str)
                if isinstance(output, tuple):
                    type_name = "tuple"
                else:
                    type_name = type(output).__name__
            except NameError as e:
                type_name = "*"
            answers.append(Answer(qnum, type_name, output_str, notes))
    return answers

def dump_results(ipynb, csv_path, default_notes={}):
    with open(csv_path, "w") as f:
        wr = csv.writer(f)
        wr.writerow(Answer._fields)
        for answer in read_code_cells(ipynb, default_notes):
            wr.writerow(answer)
    print(f"Wrote results to {csv_path}.")

def compare_bool(expected, actual, config={}):
    return expected == actual

def compare_int(expected, actual, config={}):
    return expected == actual

def compare_type(expected, actual, config={}):
    return expected == actual

def compare_float(expected, actual, config={}):
    if math.isnan(expected) and math.isnan(actual):
        return True
    tolerance = float(config.get("tolerance", 0.05))
    return math.isclose(expected, actual, rel_tol=tolerance)

def compare_str(expected, actual, config={}):
    if config.get("case") == "any":
        return expected.upper() == actual.upper()
    return expected == actual

def compare_list(expected, actual, config={}):
    if config.get("order") == "strict":
        return expected == actual
    else:
        return sorted(expected) == sorted(actual)

def compare_tuple(expected, actual, config={}):
    return expected == actual

def compare_set(expected, actual, config={}):
    if config.get("require") == "superset":
        return len(expected - actual) == 0
    else:
        return expected == actual

def compare_dict(expected, actual, config={}):
    tolerance = config.get("tolerance", None)

    if tolerance:
        if expected.keys() != actual.keys():
            return False

        for key in expected.keys():
            if not compare_float(expected[key], actual[key], {"tolerance": tolerance}):
                return False
                
        return True
    #updated function    
    for key in expected.keys():
        if key in actual.keys():
            return True
    #Todo

    return expected == actual

def compare_figure(expected, actual, config={}):
    return type(expected) == type(actual)

compare_fns = {
    "bool": compare_bool,
    "int": compare_int,
    "float": compare_float,
    "str": compare_str,
    "list": compare_list,
    "tuple": compare_tuple,
    "set": compare_set,
    "dict": compare_dict,
    "type": compare_type,
    "Figure": compare_figure
}

def parse_question_config(c):
    if c.startswith("run="):
        return {"run": c[4:]}
    config = {}
    opts = c.split(",")
    for opt in opts:
        parts = opt.split("=")
        if len(parts) != 2:
            continue
        config[parts[0]] = parts[1].strip()
    return config


def compare_func(actual_csv):
    result = {"score": 0, "errors": []}
    passing = 0
    expected_rows = {
        1: {'question': '1', 'type': 'str', 'value': "'55025'", 'notes': ': what is the geo_id for Dane County?'},
        2: {'question': '2', 'type': 'dict', 'value': "{'48': 254, '13': 159, '51': 133, '21': 120, '29': 115}", 'notes': ': how many counties do the top 5 states have?'},
        3: {'question': '3', 'type': 'dict', 'value': "{'q1': 4.76837158203125e-05, 'q2': 4.76837158203125e-05}", 'notes': ': what would each query cost, after the free tier?'},
        4: {'question': '4', 'type': 'list', 'value': "['p7']", 'notes': ': what are the datasets in your project?'},
        5: {'question': '5', 'type': 'dict', 'value': "{'Milwaukee': 46570,\n 'Dane': 38557,\n 'Waukesha': 34159,\n 'Brown': 15615,\n 'Racine': 13007,\n 'Outagamie': 11523,\n 'Kenosha': 10744,\n 'Washington': 10726,\n 'Rock': 9834,\n 'Winnebago': 9310}", 'notes': ': how many loan applications are there for each county?  (give top 10)'},
        6: {'question': '6', 'type': 'int', 'value': '1', 'notes': ': how many applications are there with your chosen income?'},
        7: {'question': '7', 'type': 'dict', 'value': "{'La Crosse': 1, 'Dane': 2, 'Brown': 1}", 'notes': ': how many new applications are there per county?'},
        8: {'question': '8', 'type': 'float', 'value': '0.291654122880204', 'notes': ": what is your model's r2_score on the HDMA dataset on which it was trained?"},
        9: {'question': '9', 'type': 'float', 'value': '0.8057773037176684', 'notes': ': what is the coefficient weight on the income column?'},
        10: {'question': '10', 'type': 'float', 'value': '0.75', 'notes': ': in the Google form dataset, what ratio of loan amounts are greater than predicted by the model?  Assume loan term is 360.'}
    }
    with open(actual_csv) as f:
        actual_rows = {int(row["question"]): dict(row) for row in csv.DictReader(f)}

    for qnum in sorted(expected_rows.keys()):
        if not qnum in actual_rows:
            continue
        expected = expected_rows[qnum]
        actual = actual_rows[qnum]
        if actual["type"] not in (expected["type"], "*"):
            err = f'Question {qnum}: expected type to be {expected["type"]}, but found {actual["type"]}'
            result["errors"].append(err)
            continue
        if not expected["type"] in compare_fns:
            raise Exception(f'Tester cannot handle type {expected["type"]} on question {qnum}')
        compare_fn = compare_fns[expected["type"]]
        config = parse_question_config(expected["notes"])
        if "run" in config:
            exec(config["run"])
        failed=True
        if qnum == 1:
            if compare_fn(eval(expected["value"]), eval(actual["value"]), config):
                passing += 1
                failed = False
                
        elif qnum == 2:
            if compare_fn(eval(expected["value"]), eval(actual["value"]), config):
                passing += 1
                failed = False                
        
        elif qnum == 3:
            expected_dict = eval(expected["value"])
            actual_dict = eval(actual["value"])

            if len(expected_dict) != len(actual_dict):
                print("len")
                failed = True
            else:
                for key, expected_value in expected_dict.items():
                    if key in actual_dict:
                        actual_value = actual_dict[key]
                        if abs(expected_value - actual_value) <= (0.00001):
                            
                            failed = False
                        else:
                            failed = True
                            break
                    else:
                        failed = True
                        break

            if not failed:
                passing += 1
        
        elif qnum == 4:
            if 'p7' in actual["value"]:
                passing += 1
                failed = False
                
        elif qnum == 5:
            if compare_fn(eval(expected["value"]), eval(actual["value"]), config):
                passing += 1
                failed = False   
                
        elif qnum == 6:
            if int(actual["value"]) >= 1 and actual["type"] == 'int':
                passing += 1
                failed = False
            
        elif qnum == 7:
            expected_keys = ['La Crosse', 'Dane', 'Brown']
            actual_dict = eval(actual["value"])

            if all(key in actual_dict for key in expected_keys):
                passing += 1
                failed = False
        
        elif qnum == 8:
            if compare_fn(eval(expected["value"]), eval(actual["value"]), config):
                passing += 1
                failed = False  
        
        elif qnum == 9:
            if compare_fn(eval(expected["value"]), eval(actual["value"]), config):
                passing += 1
                failed = False  
                
        elif qnum == 10:
            if float(actual["value"]) > 0 and float(actual["value"]) < 1:
                passing += 1
                failed = False              
            
        if failed:
            err = [
                f"Question {qnum}:",
                f"  EXPECTED: {expected['value']}",
                f"  ACTUAL: {actual['value']}",
            ]
            if expected["notes"]:
                err.append(f"  NOTES: {expected['notes']}")
            result["errors"].append("\n".join(err))

    result["missing"] = sorted(set(expected_rows.keys()) - set(actual_rows.keys()))
    score = round(100 * passing / len(expected_rows))
    result["score"] = score
    result["summary"] = f"Result: {passing} of {len(expected_rows)} passed, for an estimated score of {score}% (prior to grader deductions)."
    return result

# generates a summary of answers for SOME_NAME.ipynb in a file named SOME_NAME.csv.
# if an answer key file is specified, SOME_NAME.csv is compared to that.  If not,
# SOME_NAME.csv is compared to SOME_NAME-key.csv.
def main():
    if len(sys.argv) == 1 or len(sys.argv) >= 4:
        print("Usage: python3 tester.py <notebook.ipynb> [answer_key]")
        return

    # dump results from this notebook to a summary .csv file
    ipynb = sys.argv[1]
    assert ipynb.endswith(".ipynb")
    actual_path = ipynb.replace(".ipynb", ".csv").replace(".json", ".csv")
    dump_results(ipynb, actual_path)

    result = compare_func(actual_path)

    result_path = os.path.join(os.path.dirname(ipynb), "test.json")
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)

    # show user-friendly summary of test.json
    print("="*40)
    if len(result["errors"]):
        print(f"There were {len(result['errors'])} errors:\n")
        for err in result["errors"]:
            print(err)
            print()
    if len(result["missing"]):
        print(f'{len(result["missing"])} answers not found, for question(s):',
              ", ".join([str(m) for m in result["missing"]]))
        print()
    print(result["summary"])

if __name__ == '__main__':
     main()