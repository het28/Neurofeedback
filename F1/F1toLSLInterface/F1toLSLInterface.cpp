// F1toLSLInterface.cpp : Diese Datei enthält die Funktion "main". Hier beginnt und endet die Ausführung des Programms.
// Christoph Reichert, Project start: 27.03.2024

#include "F1toLSLInterface.hpp"
#include <json.hpp>
#include <iostream>
#include <windows.h>
#include "lsl_cpp.h"
#include "connection.hpp"
#include <algorithm>

using namespace lsl;
using nlohmann::json;
using nlohmann::detail::value_t;

connection conn;
static char const topic_device_info[] = "state/device/info";
static char const topic_sampling_start[] = "action/sampling/start";
static char const topic_sampling_stop[] = "action/sampling/stop";
static char const topic_data_samples[] = "data/samples";
static char const topic_data_event[] = "data/event";
static char const topic_battery_charge[] = "state/battery/amp/charge";
static char const topic_battery_voltage[] = "state/battery/amp/voltage";
static char const topic_battery_critical[] = "state/battery/amp/critical";

uint32_t get_beg(log_entry const& e) {
	return reinterpret_cast<uint32_t const*>(e.message.data())[0];
}

uint32_t get_end(log_entry const& e) {
	return reinterpret_cast<uint32_t const*>(e.message.data())[1];
}

uint32_t get_ndata(log_entry const& e) {
	return get_end(e) - get_beg(e);
}

uint32_t get_nchan(log_entry const& e) {
	return (e.message.size() / sizeof(uint32_t) - 2) / get_ndata(e);
}

int32_t const* get_pdata(log_entry const& e) {
	return &reinterpret_cast<int32_t const*>(e.message.data())[2];
}

struct is_distinct
{
	uint32_t prev_end;
	is_distinct() {
		prev_end = uint32_t(-1);
	}
	is_distinct(uint32_t i) {
		prev_end = i;
	}
	bool operator()(log_entry const& e) {
		if (e.topic == topic_data_samples) {
			// a log entry containing data is distinct if
			// its data begins where the previous one ended
			bool distinct = get_beg(e) != prev_end;
			prev_end = get_end(e);
			return distinct;
		}
		else {
			// every non-data log entry is distinct
			prev_end = uint32_t(-1); // reset state
			return true;
		}
	}
};

int main(int argc, char* argv[]) {
	int montageID;
	char* name;
	char* type;

	// defaults:
	name = _strdup("F1-Stream");
	type = _strdup("EEG");
	montageID = 1;

	// parse options
	int optCount = 1;
	while (argc > optCount) {
		if (strcmp(argv[optCount], "-h") == 0) {
			std::cout << "Options available:" << std::endl;
			std::cout << "-h    This help." << std::endl;
			std::cout << "-m    montage ID default is 1." << std::endl;
			std::cout << "-n    name of LSL stream,  default is F1-Stream." << std::endl;
			std::cout << "-t    type of LSL stream, default is EEG." << std::endl;			
			return 0;
		}
		else {
			if (optCount + 1 > argc) {
				std::cout << "Error in Option handling" << std::endl;
				return -1;
			}
		}
		if (strcmp(argv[optCount], "-m") == 0) {
			montageID = atoi(argv[optCount + 1]);
		}
		if (strcmp(argv[optCount], "-t") == 0) {
			type = argv[optCount + 1];
		}
		if (strcmp(argv[optCount], "-n") == 0) {
			name = argv[optCount + 1];
		}
		optCount += 2;
	}

	// connect to F1 via mqtt
	conn.connect("172.31.1.1"); // seems to be standard IP of F1
	int nchannels;
	std::string jsonstr;
	switch (montageID) {
	case 0: 
	// start sampling via mqtt topic
		jsonstr = ("{\"channel_label\":[\"Fp1\",\"Fpz\",\"Fp2\",\"F7\","
			"\"F3\",\"Fz\",\"F4\",\"F8\","
			"\"T3\",\"C3\",\"Cz\",\"C4\",\"T4\","
			"\"T5\",\"P3\",\"Pz\",\"P4\",\"T6\","
			"\"O1\",\"Oz\",\"O2\",\"A1\",\"A2\"],"
			"\"data_format\":0.0,\"gain\":12.0,"
			"\"impedance_interval\":0.0,"
			"\"layout\":1.0,"
			"\"marker_id\":\"\","
			"\"output_rate\":20.0,"
			"\"radio_bandw\":13.0,"
			"\"radio_chan\":1.0,"
			"\"reference\":[\"Fpz\"],"
			"\"sampling_rate\":500.0" "}");
		nchannels = 23;
	break;
	case 1: 
		// minimum example
	jsonstr = ("{\"channel_label\":[\"Fp2\",\"HR\"],"
		"\"data_format\":0.0,\"gain\":12.0,"
		"\"impedance_interval\":0.0,"
		"\"layout\":1.0,"
		"\"marker_id\":\"\","
		"\"output_rate\":20.0,"
		"\"radio_bandw\":13.0,"
		"\"radio_chan\":1.0,"
		"\"reference\":[\"Fpz\"],"
		"\"sampling_rate\":500.0}");
	nchannels = 2;
		break;
	default:
		break;
	}

	int srate = 500;

	const int samplesize = nchannels + 2; // last channels are event channel + sampcount
	//std::vector <float> sample(samplesize,0.0);
	float* sample = (float*)calloc(sizeof(float), samplesize);
	float scale_uV = 0.5364;


	stream_info info = lsl_create_streaminfo(name, type, samplesize, srate, (lsl_channel_format_t)cf_float32, _strdup("F1data"));
	stream_outlet* outlet = new stream_outlet(info);


	bool doTerminate = false, samplingstarted = false, isrunning = true;
	//float lastsamp = (float)1.0/(float)1000.0;
	connection::log_type log;
	float lastEvent = 0;
	unsigned long lastEventPos = 0;
	bool wasEventSent = true;
	float battV = 0;
	int battCh = 0;
	bool battCr = false;
	
	long sampcount = 0;
	double timestamp = 0;

	while (isrunning)
	{
		// poll
		if (doTerminate) {
			conn.send(topic_sampling_stop, "");
			Sleep(1000);
			isrunning = false;
		}
		log = conn.poll();
		if (!log.empty()) {
			int index = 0;
			for (connection::log_type::const_iterator it = log.begin(), nxt;
				it != log.end(); it = nxt, ++index)
			{
				nxt = next(it);				
				if (it->topic == topic_device_info && !samplingstarted) {
					json msg = json::parse(it->message);
					for (json::const_iterator jt = msg.begin(); jt != msg.end(); ++jt) {
						if (jt->type() == value_t::number_float && jt.key() == "scale_to_uV") {
									scale_uV = (float)jt.value();
								}					
					}

					std::cout << it->topic << ": " << it->message << std::endl;
					conn.send(topic_sampling_start, jsonstr);
					std::cout << "Now sending data until LSHIFT + ESC is pressed... " << std::endl;
				}
				else if (it->topic == topic_data_samples) {					
					// find the next log entry which is distinct, and while
					// doing that, calculate the total number of samples
					// in all continuous log entries
					uint32_t ndata = get_ndata(*it);
					is_distinct check{ get_end(*it) };
					nxt = find_if(nxt, log.cend(), [&](log_entry const& e) {
						bool distinct = check(e);
						if (!distinct) ndata += get_ndata(e);
						return distinct;
						});
					int nChan = get_nchan(*it);
					if (nChan!=nchannels){
						//TODO: throw some error message
						std::cerr << "error in number of channels! " << nChan << "!=" << nchannels <<"\n";
					}

					//int32_t* pint = new int32_t[nChan * ndata];
					//uint8_t* p = static_cast<uint8_t*>(*pint);					
					int32_t* p = new int32_t[nChan * ndata];
					int sampAvailable;
					int sampsiz = nChan * sizeof(int32_t);
					uint32_t pos = get_beg(*it);
					for (auto j = it; j != nxt; ++j) {
						uint32_t n = j->message.size() - 2 * sizeof(int32_t);						
						sampAvailable = n / sampsiz;
						memcpy(p, get_pdata(*j), n);
						for (int k = 0; k < sampAvailable; k++) {
														
							
							for (int sc = 0; sc < nChan; sc++) {
								sample[sc] = (float)(p[k*nChan + sc]) * scale_uV;
							}
							
							if (!wasEventSent && pos>=lastEventPos) {//  handle the event channel
								sample[nChan] = lastEvent;
								wasEventSent = true;
							}
							else sample[nChan] = 0;
							sample[nChan + 1] = (float)pos;
							pos++;
							timestamp = timestamp + 1.0 / (double)srate;
							outlet->push_sample(sample,timestamp);
							sampcount++;
						}
						p += nChan*sampAvailable; // should be same as n/sizeof(int32_t)
					}					

				}
				else if (it->topic == topic_data_event) {
					json msg = json::parse(it->message);
					for (json::const_iterator jt = msg.begin(); jt != msg.end(); ++jt) {
						if (jt->type() == value_t::number_unsigned && jt.key() == "kind") { //
							lastEvent = (float)jt.value();
						}
						if (jt->type() == value_t::number_unsigned && jt.key() == "lower") { //
							lastEventPos = (unsigned long)jt.value();
							wasEventSent = false;
						}
					}
					std::cout << it->topic << ": " << it->message << std::endl;
				}
				else if (it->topic == topic_battery_charge) {
					battCh = stoi(it->message);										
				}
				else if (it->topic == topic_battery_voltage) {
					battV = stof(it->message);
				}
				else if (it->topic == topic_battery_critical) {
					battCr = it->message == "true";
				}
				else {
					std::cout << it->topic << ": " << it->message << std::endl;
				}
			}

		}
		if (GetKeyState(VK_ESCAPE) & 0x8000 && GetKeyState(VK_LSHIFT) & 0x8000) doTerminate = true;
		if (GetKeyState(VK_F1) & 0x8000 || battCr) // report status on key press
		{
			std::cout << "Count: " << sampcount << " (" << (float)sampcount / srate;
			std::cout <<	"s) Battery: " << battV << "V (" << battCh << "%) " << (battCr?"!critical!":"OK") << std::endl;
			Sleep(100);
		}
		Sleep(1);
	}
    std::cout << "byebye!\n";
	if (outlet)
		delete outlet;	
	Sleep(500);
	conn.disconnect(); // disconnect from F1 via mqtt
}
