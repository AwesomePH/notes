from caffe.proto import caffe_pb2
import google.protobuf.text_format as txtf
import sys
import os

def ParseByText(file):
  types = dict()
  with open(file) as f:
    for l in f.readlines():
      pos = l.find("type:")
      if pos > 0:
        curtype = l[pos+6:].strip()
        if curtype in types.keys():
          types[curtype] += 1
        else:
          types[curtype] = 1
  return types



if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == '-h':
        print("Usage: GetCaffeOps.py: input_pt")
        exit(1)
    net = caffe_pb2.NetParameter()
    filename = sys.argv[1]
    with open(filename) as f:
        s = f.read()
        txtf.Merge(s, net)
    layers = net.layer
    types = dict()

    if len(layers) == 0 and len(net.layers) > 0:
      types = ParseByText(filename)
    else: 
      print("net layers count: ", len(layers))

      for i in range(0, len(layers)):
        l = layers[i]
        # import pdb; pdb.set_trace()
        if l.type in types.keys():
          types[l.type] += 1
        else:
          types[l.type] = 1
    
    print("\nPrinting caffe layer types:")
    for t in types.keys():
      print(t)

    print("\nPrinting keys and counts:")
    for (k,v) in types.items():
      print(str(k) + " - " + str(v))


