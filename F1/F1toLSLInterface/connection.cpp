

#define BOOST_ERROR_CODE_HEADER_ONLY
#define MQTT_NO_TLS
#define BOOST_USE_WINDOWS_H // added by C.R.

#include <boost/asio.hpp>
#include <mqtt_client_cpp.hpp>
#include <thread>
#include <cstdlib>
#include "connection.hpp"

using client_type = mqtt::client<boost::asio::ip::tcp::socket, mqtt::null_strand>;

static char const topic_data_samples[] = "data/samples";

struct connection::impl : std::enable_shared_from_this<impl>
{
    impl() = default;
    ~impl();
    
    void connect(std::string&& host);
    void on_connect(bool sp, std::uint8_t rc);
    void on_close();
    void on_error(boost::system::error_code const& ec);
  /*
    void on_receive(std::uint8_t header,
         boost::optional<std::uint16_t> packet_id,
         std::string&& topic, std::string&& msg);
    */

    void add_to_log(log_entry::direction dir, std::string&& topic, std::string&& msg);
    
    boost::asio::io_service      ios_;
    std::thread                  thread_;
    std::shared_ptr<client_type> client_;
    std::string                  sampling_active_;
    std::string                  device_info_;
    
    connection::log_type         log_;
    std::mutex                   log_mutex_;
};

void connection::connect(std::string host) {
    impl_.reset();
    impl_ = std::make_shared<impl>();
    impl_->connect(std::move(host));
}

void connection::disconnect() {
    impl_.reset();
}

void connection::send(std::string t, std::string m)
{
    std::shared_ptr<impl> p = impl_; // keep alive
    if (!p)
        throw std::runtime_error("Not connected.");
    p->ios_.post([p, t = std::move(t), m = std::move(m)] () mutable {
        std::shared_ptr<client_type> c = p->client_;
        if (!c) return;
        c->publish_at_least_once(t, m);
        p->add_to_log(log_entry::send, std::move(t), std::move(m));
    });    
}

auto connection::poll() -> log_type {
    std::shared_ptr<impl> p = impl_; // keep alive
    if (!p)
        throw std::runtime_error("Not connected.");    
    log_type log;
    std::lock_guard<std::mutex> lock(p->log_mutex_);
    if (!p->log_.empty()) {
        log.reserve(512);
        std::swap(log, p->log_);
    }
    return log;
}

void connection::impl::connect(std::string&& host)
{
    std::weak_ptr<impl> w = shared_from_this();
    client_ = mqtt::make_client_no_strand(ios_, std::move(host), 1883);
    client_->set_client_id("f1stream");
    client_->set_clean_session(true);
    client_->set_connack_handler([w] (bool sp, std::uint8_t rc) {
        auto p = w.lock();
        if (p) p->on_connect(sp, rc);
        return rc == mqtt::connect_return_code::accepted;
    });
    client_->set_close_handler([w] {
        auto p = w.lock();
        if (p) p->on_close();
    });
    client_->set_error_handler([w] (boost::system::error_code const& ec) {
        auto p = w.lock();
        if (p) p->on_error(ec);
    });
    client_->set_publish_handler([w] (std::uint8_t header,
                                      boost::optional<std::uint16_t> packet_id,
                                      std::string&& topic,
                                      std::string&& msg) {
        auto p = w.lock();
        if (p) p->add_to_log(log_entry::recv, std::move(topic), std::move(msg));
        return true;
    });
    client_->set_puback_handler ([] (std::uint16_t) { return true; });
    client_->set_pubrec_handler ([] (std::uint16_t) { return true; });
    client_->set_pubcomp_handler([] (std::uint16_t) { return true; });
    client_->connect();
    thread_ = std::thread([this] { ios_.run(); });
}

connection::impl::~impl()
{
    if (client_) {
        client_->disconnect();
        client_.reset();
    }
    if (thread_.joinable()) {
        ios_.stop();
        thread_.join();
    }
}

void connection::impl::add_to_log(log_entry::direction d, std::string&& t, std::string&& m)
{
    std::lock_guard<std::mutex> lock(log_mutex_);
    log_.emplace_back(d, std::move(t), std::move(m));
}

void connection::impl::on_connect(bool sp, std::uint8_t rc)
{
    add_to_log(log_entry::recv, "mqtt", std::string("\"") + mqtt::connect_return_code_to_str(rc) + "\"");
    if (rc == mqtt::connect_return_code::accepted) {
        client_->publish_at_least_once("action/impedance/stop", "1");
        client_->publish_at_least_once("action/sampling/stop", "1");
        client_->subscribe("state/#", mqtt::qos::at_least_once);
        client_->subscribe("error",   mqtt::qos::at_least_once);
        client_->subscribe("data/#",  mqtt::qos::at_most_once);
    }
}

void connection::impl::on_close()
{
    add_to_log(log_entry::recv, "mqtt", "\"Connection lost\"");
}

void connection::impl::on_error(boost::system::error_code const& ec)
{
    add_to_log(log_entry::recv, "mqtt", std::string("\"") + ec.message() + "\"");
}



