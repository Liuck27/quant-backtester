#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <numeric>
#include <string>
#include <optional>

namespace py = pybind11;

struct MinimalMarketEvent {
    std::string time;
    std::string symbol;
    double price;
    int volume;
};

struct MinimalSignalEvent {
    std::string time;
    std::string symbol;
    std::string signal_type;
    double strength;
};

class CppMovingAverageCrossStrategy {
public:
    CppMovingAverageCrossStrategy(int short_window, int long_window)
        : short_window_(short_window), long_window_(long_window), bought_(false) {}

    // Original method (compatible with full Event objects)
    std::optional<MinimalSignalEvent> calculate_signals(const MinimalMarketEvent& event) {
        prices_.push_back(event.price);
        
        // Warm-up
        if (prices_.size() < (size_t)long_window_) {
            return std::nullopt;
        }

        double short_sma = calculate_sma(short_window_);
        double long_sma = calculate_sma(long_window_);

        std::string signal_type = "";
        
        if (short_sma > long_sma && !bought_) {
            bought_ = true;
            signal_type = "LONG";
        } else if (short_sma < long_sma && bought_) {
            bought_ = false;
            signal_type = "EXIT";
        }

        if (!signal_type.empty()) {
            return MinimalSignalEvent{event.time, event.symbol, signal_type, 1.0};
        }
        return std::nullopt;
    }

    // Fast path: Just pass price, return code
    // 0: None, 1: LONG, -1: EXIT
    int calculate_signal_fast(double price) {
        prices_.push_back(price);

        if (prices_.size() < (size_t)long_window_) {
            return 0;
        }

        double short_sma = calculate_sma(short_window_);
        double long_sma = calculate_sma(long_window_);

        if (short_sma > long_sma && !bought_) {
            bought_ = true;
            return 1;
        } else if (short_sma < long_sma && bought_) {
            bought_ = false;
            return -1;
        }
        return 0;
    }

    bool is_bought() const { return bought_; }
    std::vector<double> get_prices() const { return prices_; }

private:
    int short_window_;
    int long_window_;
    bool bought_;
    std::vector<double> prices_;

    double calculate_sma(int window) {
        double sum = 0.0;
        // Iterate backwards from end
        size_t n = prices_.size();
        for (size_t i = 0; i < (size_t)window; ++i) {
            sum += prices_[n - 1 - i];
        }
        return sum / window;
    }
};

PYBIND11_MODULE(quant_strategy_cpp, m) {
    py::class_<MinimalMarketEvent>(m, "MinimalMarketEvent")
        .def(py::init<std::string, std::string, double, int>())
        .def_readwrite("time", &MinimalMarketEvent::time)
        .def_readwrite("symbol", &MinimalMarketEvent::symbol)
        .def_readwrite("price", &MinimalMarketEvent::price)
        .def_readwrite("volume", &MinimalMarketEvent::volume);

    py::class_<MinimalSignalEvent>(m, "MinimalSignalEvent")
        .def(py::init<std::string, std::string, std::string, double>())
        .def_readwrite("time", &MinimalSignalEvent::time)
        .def_readwrite("symbol", &MinimalSignalEvent::symbol)
        .def_readwrite("signal_type", &MinimalSignalEvent::signal_type)
        .def_readwrite("strength", &MinimalSignalEvent::strength);

    py::class_<CppMovingAverageCrossStrategy>(m, "CppMovingAverageCrossStrategy")
        .def(py::init<int, int>(), py::arg("short_window") = 10, py::arg("long_window") = 30)
        .def("calculate_signals", &CppMovingAverageCrossStrategy::calculate_signals)
        .def("calculate_signal_fast", &CppMovingAverageCrossStrategy::calculate_signal_fast)
        .def("is_bought", &CppMovingAverageCrossStrategy::is_bought)
        .def("get_prices", &CppMovingAverageCrossStrategy::get_prices);
}
