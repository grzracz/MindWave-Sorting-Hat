name = "sample_output.txt"

f = open(name, "r")
g = open("csv-" + name, "w+")
g.write("Signal, Attention, Meditation, Delta, Theta, low Alpha, "
        "high Alpha, low Beta, high Beta, low Gamma, high Gamma\n")
for line in f:
    if line[:5] == "Signa":
        g.write(line[(line.find(":") + 2):(line.find("t", line.find(":") + 1))-1] + ", ")
    if line[:5] == "Atten":
        g.write(line[(line.find(":") + 2):(line.find("t", line.find(":") + 1))-1] + ", ")
    if line[:5] == "Medit":
        g.write(line[(line.find(":") + 2):(line.find("t", line.find(":") + 1))-1] + ", ")
    if line[:5] == "Delta":
        g.write(line[(line.find(":") + 2):(line.find("t", line.find(":") + 1))-1] + ", ")
    if line[:5] == "Theta":
        g.write(line[(line.find(":") + 2):(line.find("t", line.find(":") + 1))-1] + ", ")
    if line[:5] == "low A":
        g.write(line[(line.find(":") + 2):(line.find("t", line.find(":") + 1))-1] + ", ")
    if line[:6] == "high A":
        g.write(line[(line.find(":") + 2):(line.find("t", line.find(":") + 1))-1] + ", ")
    if line[:5] == "low B":
        g.write(line[(line.find(":") + 2):(line.find("t", line.find(":") + 1))-1] + ", ")
    if line[:6] == "high B":
        g.write(line[(line.find(":") + 2):(line.find("t", line.find(":") + 1))-1] + ", ")
    if line[:5] == "low G":
        g.write(line[(line.find(":") + 2):(line.find("t", line.find(":") + 1))-1] + ", ")
    if line[:6] == "high G":
        g.write(line[(line.find(":") + 2):(line.find("t", line.find(":") + 1))-1] + "\n")

