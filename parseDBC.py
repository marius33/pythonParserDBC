import sys
import re


class Signal:

    def __init__(self):
        self.name = ""
        self.msb = -1
        self.len = -1
        self.mul = -1
        self.offset = -1
        self.unit = ""
        self.max = -1
        self.min = -1
        self.receivers = []
        self.values = []


class Message:

    def __init__(self):
        self.id = -1
        self.len = -1
        self.name = ""
        self.emitter = ""
        self.period = -1
        self.type = ""
        self.signals = []

    def has_receiver(self, rec):
        for signal in self.signals:
            for receiver in signal.receivers:
                if rec == receiver:
                    return True

        return False

def msb2lsb(messagelength, signallength, signalmsb):
    byte = (messagelength - 1) - signalmsb // 8
    bit = signalmsb % 8
    msb = byte*8+bit
    lsb = msb - (signallength - 1)
    return lsb

def raw(signal, physical):
    raw = physical/signal.mul - signal.offset
    raw << msb2lsb(signal.msb)
    return raw


with open(sys.argv[1], 'r') as f:

    foundMessages = []
    text = f.read()
    mm = re.findall(r"(BO_\s+[0-9]{1,4}\s+[0-9a-zA-Z_]+:\s+[0-9]\s+[0-9a-zA-Z_]+\n(.+\n)+)", text)
    mm = [re.sub(r"(BO_)|(SG_)|(@0\+)|\(|\)|\[|\]|:", "", x[0]) for x in mm]
    mm = [re.sub(r",|\|", " ", x).strip() for x in mm]

    for message in mm:
        msg = Message()
        foundMessages.append(msg)

        lines = message.split("\n")
        msgLine = lines[0].split()

        msg.id = msgLine[0]
        msg.name = msgLine[1]
        msg.len = int(msgLine[2])
        msg.emitter = msgLine[3]

        for signalLine in [x.split() for x in lines[1:]]:
            sgnl = Signal()
            msg.signals.append(sgnl)
            sgnl.name = signalLine[0]
            sgnl.msb = int(signalLine[1])
            sgnl.len = int(signalLine[2])
            sgnl.mul = float(signalLine[3])
            sgnl.offset = float(signalLine[4])
            sgnl.min = float(signalLine[5])
            sgnl.max = float(signalLine[6])
            sgnl.unit = signalLine[7].replace(r"\"", "")
            sgnl.receivers = signalLine[8:]

            signalPattern = "VAL_ "+msg.id+" "+sgnl.name+".+"

            match = re.search(signalPattern, text)
            if match:
                words = re.findall(r"\"(.+?)\"", match.group())
                words = [x.replace("\"", "").strip() for x in words]
                sgnl.values = words

        messageTypePattern = "BA_ \"FrameType\" BO_ " + msg.id + " .+"
        messageCyclePattern = "BA_ \"CycleTime\" BO_ " + msg.id + " .+"

        match = re.search(messageTypePattern, text)
        if match:
            words = re.findall(r"\"(.+?)\"", match.group())
            msg.type = words[1].replace("\"", "").strip()

        match = re.search(messageCyclePattern, text)
        if match:
            words = match.group().split()
            msg.period = int(words[4][:-1])

    if sys.argv[2] == 'c' or sys.argv[2] == 'C':

        with open(sys.argv[3]+"\\candb_messages.h", 'w') as h:

            h.write("#ifndef CANDB_MESSAGES\n"
                    "#define CANDB_MESSAGES\n"
                    "#include \"candb.h\"\n"
                    "\n"
                    "void candb_messages_init(void);\n"
                    "\n")

            with open(sys.argv[3]+"\\candb_messages.c", 'w') as c:

                c.write("#include \"candb_messages.h\"\n"
                        "\n"
                        "\n")

                listInit = "CANMessage* messages[MESSAGES_LENGTH] = {"
                messagesLength = 0
                signalInit = "void candb_messages_init(void){\n"
                # add after "...if x" a filter for messages if needed
                for message in [x for x in foundMessages if (x.has_receiver("") and x.emitter != "" and "" not in x.name)]:
                    h.write("extern CANMessage "+message.name+";\n")
                    c.write("CANMessage " + message.name + " = {"
                            + str(message.id)+", "
                            + str(message.len)+", 0, "
                            + str(message.period)+", 0};\n")
                    listInit += "&"+message.name+", "

                    # add after "...if x" a filter for signals if needed
                    for signal in [x for x in message.signals if ("" in x.receivers)]:
                        h.write("\textern CANSignal "+message.name+"_"+signal.name+";\n")
                        c.write("\tCANSignal " + message.name+"_"+signal.name + " = {"
                                + str(signal.len)+", "
                                + str(msb2lsb(message.len, signal.len, signal.msb))+", &"
                                + message.name+"};\n")
                        signalInit += "\tcandb_set_signal(&" + signal.name+", ?);\n"
                    h.write("\n")
                    c.write("\n")
                    messagesLength += 1

                listInit = listInit[:-2]+"};\n"
                signalInit += "};\n"
                c.write("\n"+listInit)
                c.write("\n"+signalInit)
                h.write("#define MESSAGES_LENGTH "+str(messagesLength)+";\n")
                h.write("extern CANMessage* messages[MESSAGES_LENGTH];\n")
                h.write("#endif")