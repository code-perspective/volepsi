import sys
with open('volePSI/fileBased.cpp', 'r') as f:
    text = f.read()

# Add includes
if 'BufferingSocket' not in text:
    text = text.replace('#include "coproto/Socket/AsioSocket.h"', '#include "coproto/Socket/AsioSocket.h"\n#include "coproto/Socket/BufferingSocket.h"\n#include <thread>\n#include <unistd.h>')

# Add communicateViaFiles function
func = """
    void communicateViaFiles(macoro::eager_task<>& protocol, bool sender, coproto::BufferingSocket& sock)
    {
        int s = 0, r = 0;
        std::string me = sender ? "sender" : "recver";
        std::string them = !sender ? "sender" : "recver";
        auto write = [&](){
            auto b = sock.getOutbound();
            if (b && b->size()) {
                std::ofstream message;
                auto temp = me + ".tmp";
                auto file = me + "_" + std::to_string(s) + ".bin";
                message.open(temp, std::ios::binary | std::ios::trunc);
                message.write((char*)b->data(), b->size());
                message.close();
                rename(temp.c_str(), file.c_str());
                ++s;
            }
        };
        auto read = [&]() {
            std::ifstream message;
            auto file = them + "_" + std::to_string(r) + ".bin";
            while (message.is_open() == false) {
                message.open(file, std::ios::binary);
                if (!message.is_open()) std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
            auto fsize = filesize(message);
            std::vector<oc::u8> buff(fsize);
            message.read((char*)buff.data(), fsize);
            message.close();
            std::remove(file.c_str());
            ++r;
            sock.processInbound(buff);
        };
        if (sender) write();
        while (protocol.is_ready() == false) {
            read();
            write();
        }
    }
"""
if 'communicateViaFiles' not in text:
    text = text.replace('namespace volePSI\n{', 'namespace volePSI\n{\n' + func)

# Replace conn block
target_conn = """            if (!quiet)
                std::cout << "connecting as " << (tls ? "tls " : "") << (isServer ? "server" : "client") << " at address " << ip << std::flush;
            coproto::Socket chl;
            auto connBegin = timer.setTimePoint("");"""
new_conn = """            coproto::Socket chl;
            coproto::BufferingSocket sock;
            bool useFilePassing = cmd.isSet("file-passing");
            auto connBegin = timer.setTimePoint("");
            
            if (useFilePassing) {
               if (!quiet) std::cout << "using file-based message passing" << std::flush;
            } else {
               if (!quiet) std::cout << "connecting as " << (tls ? "tls " : "") << (isServer ? "server" : "client") << " at address " << ip << std::flush;
"""
if 'useFilePassing' not in text and target_conn in text:
    text = text.replace(target_conn, new_conn)
    text = text.replace('throw std::runtime_error("COPROTO_ENABLE_BOOST must be define (via cmake) to use tcp sockets. " COPROTO_LOCATION);\n#endif\n            }', 'throw std::runtime_error("COPROTO_ENABLE_BOOST must be define (via cmake) to use tcp sockets. " COPROTO_LOCATION);\n#endif\n            }\n            }')

# Replace size validation
target_size = """            if (set.size() != cmd.getOr((r == Role::Sender) ? "senderSize" : "receiverSize", set.size()))
                throw std::runtime_error("File does not contain the specified set size.");
            u64 theirSize;
            macoro::sync_wait(chl.send(set.size()));
            macoro::sync_wait(chl.recv(theirSize));

            if (theirSize != cmd.getOr((r != Role::Sender) ? "senderSize" : "receiverSize", theirSize))
                throw std::runtime_error("Other party's set size does not match.");"""
new_size = """            if (set.size() != cmd.getOr((r == Role::Sender) ? "senderSize" : "receiverSize", set.size()))
                throw std::runtime_error("File does not contain the specified set size.");
            u64 theirSize = 0;
            if (useFilePassing) {
                theirSize = cmd.getOr((r != Role::Sender) ? "senderSize" : "receiverSize", set.size());
            } else {
                macoro::sync_wait(chl.send(set.size()));
                macoro::sync_wait(chl.recv(theirSize));
                if (theirSize != cmd.getOr((r != Role::Sender) ? "senderSize" : "receiverSize", theirSize))
                    throw std::runtime_error("Other party's set size does not match.");
            }"""
if 'theirSize = 0;' not in text and target_size in text:
    text = text.replace(target_size, new_size)

# Replace Sender run
target_sender = """                sender.init(set.size(), theirSize, statSetParam, seed, mal, 1);
                macoro::sync_wait(sender.run(set, chl));
                macoro::sync_wait(chl.flush());"""
new_sender = """                sender.init(set.size(), theirSize, statSetParam, seed, mal, 1);
                if (useFilePassing) {
                    auto protocol = sender.run(set, sock) | macoro::make_eager();
                    communicateViaFiles(protocol, true, sock);
                } else {
                    macoro::sync_wait(sender.run(set, chl));
                    macoro::sync_wait(chl.flush());
                }"""
if 'protocol = sender.run(set, sock)' not in text and target_sender in text:
    text = text.replace(target_sender, new_sender)

# Replace Receiver run
target_recver = """                recver.init(theirSize, set.size(), statSetParam, seed, mal, 1);
                macoro::sync_wait(recver.run(set, chl));
                macoro::sync_wait(chl.flush());"""
new_recver = """                recver.init(theirSize, set.size(), statSetParam, seed, mal, 1);
                if (useFilePassing) {
                    auto protocol = recver.run(set, sock) | macoro::make_eager();
                    communicateViaFiles(protocol, false, sock);
                } else {
                    macoro::sync_wait(recver.run(set, chl));
                    macoro::sync_wait(chl.flush());
                }"""
if 'protocol = recver.run(set, sock)' not in text and target_recver in text:
    text = text.replace(target_recver, new_recver)

with open('volePSI/fileBased.cpp', 'w') as f:
    f.write(text)
print("done patching fileBased.cpp")
