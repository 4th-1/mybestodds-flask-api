import os, json

ROOT = r"C:\MyBestOdds\jackpot_system_v3\data\subscribers"

for root, dirs, files in os.walk(ROOT):
    for f in files:
        if f.endswith(".json"):
            fp = os.path.join(root, f)
            try:
                with open(fp, "r") as infile:
                    data = json.load(infile)

                # Update coverage dates
                data["coverage_start"] = "2025-09-01"
                data["coverage_end"]   = "2025-11-10"

                with open(fp, "w") as outfile:
                    json.dump(data, outfile, indent=2)

                print("Updated:", f)

            except Exception as e:
                print("Error updating", f, ":", str(e))
