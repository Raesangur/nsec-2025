#!/usr/bin/env python3
import re
import csv
import models
import xmltodict

from datetime import datetime
from os import chmod, unlink
from os.path import join
from flask import Flask, request, send_file, render_template, url_for

app = Flask(__name__)
app.config["MAX_CONTENT_PATH"] = 1024 * 1024

"""
TODO: Implement a way to reboot the machine?
"""

@app.route("/", methods=["GET","POST"])
def index():
    ret = []

    if request.method == "POST":
        content_dict = xmltodict.parse(request.form["data"])

        try:
            if not "query" in content_dict:
                return ret

            query = content_dict["query"]

            indexes = [*range(5)]
            if "select" in query:
                if not "id" in query["select"]: indexes.remove(0)
                if not "name" in query["select"]: indexes.remove(1)
                if not "class" in query["select"]: indexes.remove(2)
                if not "purchase_date" in query["select"]: indexes.remove(3)
                if not "allergies" in query["select"]: indexes.remove(4)
            
            data = models.load_data()

            if not "model" in query:
                return ret

            d = [*data]
            for model in query["model"] if isinstance(query["model"], list) else [query["model"]]:
                if not "@name" in model or not model["@name"] in dir(models) or not "operator" in model or not "values" in model:
                    continue

                m = getattr(models, model["@name"])

                for operator in model["operator"] if isinstance(model["operator"], list) else [model["operator"]]:
                    r = []
                    
                    if not operator in dir(m):
                        continue
                    for row in range(len(d)-1, -1, -1) or range(len(r)-1, -1, -1):
                        l = d or r
                        for cell in range(len(l[row])):
                            if not cell in indexes: continue
                            g = getattr(m, operator)(l[row][cell], **model["values"] if "values" in model and isinstance(model["values"], dict) else {})

                            if g == True:
                                r.append(l[row])
                                break
                            elif g != False:
                                raise Exception(g)
                    d = r
                
                [ret.append(i) for i in d if not i in ret]
        except Exception as e:
            import traceback
            return traceback.format_exc()

        return sorted(ret, key=lambda x: x[0])
    else:
        data = models.load_data()

        return render_template("index.html", data=data)

@app.route("/upload", methods=["POST"])
def upload():
    f = request.files["file"]
    mode = request.form.get("mode", '644')
    
    if not re.match(r"^[23567][0-7]{2}$", mode):
        return f"Invalid mode: '{mode}'"

    path = join("uploads", re.sub(r"[^a-zA-Z0-9\-_\.]", "", f.filename).replace("..", ""))

    f.save(path)
    chmod(path, int(mode[0]) << 0x6 | int(mode[1]) << 0x3 | int(mode[2]))

    # TODO: Implement the code to add and merge new passengers.
    #       Until then, the task is done manually.
    data = models.load_data()
    with open(path,"r") as f:
        passengers = []
        reader = csv.DictReader(f, fieldnames=["id", "name", "class", "purchase_date", "allergies"])
        firstline = True
        for line in reader:
            if firstline:
                firstline = False
                if line["id"] == "id" and line["name"] == "name" and line["class"] == "class" and line["purchase_date"] == "purchase_date" and line["allergies"] == "allergies":
                    continue

            if line["id"] is None or line["name"] is None or line["class"] is None or line["purchase_date"] is None or line["allergies"] is None or not line["id"].isnumeric() or not line["class"].isnumeric() or not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", line["purchase_date"]):
                continue

            found = False
            for i in range(len(data)):
                if data[i][0] == int(line["id"]):
                    found = True
                    data[i][1] = line["name"]
                    data[i][2] = int(line["class"])
                    data[i][3] = datetime.fromisoformat(line["purchase_date"])
                    data[i][4] = line["allergies"]
                    break

            if not found:
                data.append(line)

    # TODO: save_data does nothing yet, it's not implemented.
    models.save_data(data)

    unlink(path)

    return "ok"

@app.route("/download", methods=["GET"])
def download():
    return send_file("app.py", as_attachment=True)
