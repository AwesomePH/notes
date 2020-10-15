import sys

'''
receive a print(graph) log file and print the ops in log file
'''

s = set()

if __name__ == "__main__":
    input = sys.argv[1]
    with open(input) as f:
        lines = f.readlines()
        for l in lines:
            if l.find("::") != -1 :
                beg = l.find(" = ")
                if beg == -1:
                    print(l)
                end = l.find("[", beg)
                if end ==  -1:
                    end = l.find("(", beg)
                if end == -1:
                    print(l)
                beg = beg+2
                op = l[beg:end]
                s.add(op)
    for i in s:
        print(i)