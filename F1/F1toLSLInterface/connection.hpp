
#include <memory>
#include <vector>
#include <array>
#include <string>
#include <chrono>

struct log_entry
{
    using clock_type = std::chrono::system_clock;
    using time_point = clock_type::time_point;
    enum direction { send, recv };
    
    log_entry(direction d, std::string t, std::string m)
    : timestamp(clock_type::now()), dir(d)
    , topic(std::move(t)), message(std::move(m))
    {}
    
    time_point  timestamp;
    direction   dir;
    std::string topic;
    std::string message;
};

class connection
{
public:
    using log_type = std::vector<log_entry>;
    
    void connect(std::string host);
    void disconnect();
    
    void send(std::string topic, std::string msg);
    log_type poll();

private:
    struct impl;
    std::shared_ptr<impl> impl_;
};
