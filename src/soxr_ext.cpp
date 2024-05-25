#include <stdint.h>
#include <algorithm>
#include <cmath>
#include <typeinfo>

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>

#include "soxr.h"


using std::type_info;

namespace nb = nanobind;
using namespace nb::literals;


// C type to soxr_io_spec_t
static soxr_datatype_t to_soxr_datatype(const type_info& ntype) {
    if (ntype == typeid(float))
        return SOXR_FLOAT32_I;
    else if (ntype ==typeid(double))
        return SOXR_FLOAT64_I;
    else if (ntype == typeid(int32_t))
        return SOXR_INT32_I;
    else if (ntype == typeid(int16_t))
        return SOXR_INT16_I;
    else
        throw nb::type_error("Data type not support");
}

class CySoxr {
    soxr_t _soxr;
    double _in_rate;
    double _out_rate;
    soxr_datatype_t _ntype;
    unsigned _channels;
    bool _ended;

public:
    CySoxr(double in_rate, double out_rate, unsigned num_channels, soxr_datatype_t ntype, unsigned long quality) {
        _in_rate = in_rate;
        _out_rate = out_rate;
        _ntype = ntype;
        _channels = num_channels;
        _ended = false;

        soxr_error_t err = NULL;
        soxr_io_spec_t io_spec = soxr_io_spec(ntype, ntype);
        soxr_quality_spec_t quality_spec = soxr_quality_spec(quality, 0);

        _soxr = soxr_create(
            in_rate, out_rate, num_channels,
            &err, &io_spec, &quality_spec, NULL);

        if (err != NULL) {
            throw std::runtime_error(err);
        }
    }

    ~CySoxr() {
        soxr_delete(_soxr);
    }

    template <typename T>
    auto process(nb::ndarray<const T, nb::ndim<2>, nb::c_contig, nb::device::cpu> x, bool last=false) {
        size_t ilen = x.shape(0);
        size_t olen = 2 * ilen * _out_rate / _in_rate + 1;
        unsigned channels = x.shape(1);

        if (_ended)
            throw std::runtime_error("Input after last input");

        if (channels != _channels)
            throw std::invalid_argument("Channel num mismatch");

        const soxr_datatype_t ntype = to_soxr_datatype(typeid(T));

        if (ntype != _ntype)
            throw nb::type_error("Data type mismatch");

        T *y = new T[olen * channels] { 0 };

        soxr_error_t err = NULL;
        size_t odone = 0;
        err = soxr_process(
            _soxr,
            x.data(), ilen, NULL,
            y, olen, &odone);

        // flush if last input
        if (last) {
            _ended = true;
            size_t delay = soxr_delay(_soxr) + .5;

            if (0 < delay) {
                T *last_buf = new T[(odone+delay) * channels] { 0 };
                std::copy_n(y, odone*channels, last_buf);
                delete[] y;

                size_t ldone = 0;
                err = soxr_process(
                    _soxr,
                    NULL, 0, NULL,
                    &last_buf[odone*channels], delay, &ldone);

                nb::capsule last_owner(last_buf, [](void *p) noexcept {
                    delete[] (T *) p;
                });
                return nb::ndarray<nb::numpy, T>(last_buf, { odone+ldone, channels }, last_owner);
            }
        }
        // Delete 'y' when the 'owner' capsule expires
        nb::capsule owner(y, [](void *p) noexcept {
            delete[] (T *) p;
        });
        return nb::ndarray<nb::numpy, T>(y, { odone, channels }, owner);
    }
};


template <typename T>
auto cysoxr_divide_proc(double in_rate, double out_rate,
        nb::ndarray<T, nb::ndim<2>, nb::c_contig, nb::device::cpu> x,
        unsigned long quality) {
    size_t ilen = x.shape(0);
    size_t olen = ilen * out_rate / in_rate + 1;
    size_t chunk_len = 48000 * in_rate / out_rate;
    unsigned channels = x.shape(1);

    const soxr_datatype_t ntype = to_soxr_datatype(typeid(T));

    // init soxr
    soxr_error_t err = NULL;
    const soxr_io_spec_t io_spec = soxr_io_spec(ntype, ntype);
    const soxr_quality_spec_t quality_spec = soxr_quality_spec(quality, 0);

    soxr_t soxr = soxr_create(
        in_rate, out_rate, channels,
        &err, &io_spec, &quality_spec, NULL);

    if (err != NULL)
        throw std::runtime_error(err);

    // alloc
    T *y = new T[olen * channels] { 0 };

    // divide and process
    size_t odone = 0;
    size_t out_pos = 0;
    size_t idx = 0;
    // with nogil:
    while (idx + chunk_len < ilen) {
        err = soxr_process(
            soxr,
            &x.data()[idx*channels], chunk_len, NULL,
            &y[out_pos*channels], olen-out_pos, &odone);
        out_pos += odone;
        idx += chunk_len;
    }

    // last chunk
    if (idx < ilen) {
        err = soxr_process(
            soxr,
            &x.data()[idx*channels], ilen-idx, NULL,
            &y[out_pos*channels], olen-out_pos, &odone);
        out_pos += odone;
    }

    // flush
    if (out_pos < olen) {
        err = soxr_process(
            soxr,
            NULL, 0, NULL,
            &y[out_pos*channels], olen-out_pos, &odone);
        out_pos += odone;
    }

    if (err != NULL)
        throw std::runtime_error(err);

    // destruct
    soxr_delete(soxr);

    // Delete 'y' when the 'owner' capsule expires
    nb::capsule owner(y, [](void *p) noexcept {
       delete[] (T *) p;
    });
    return nb::ndarray<nb::numpy, T>(y, { out_pos, channels }, owner);
}


template <typename T>
auto cysoxr_oneshot(
        double in_rate, double out_rate,
        nb::ndarray<T, nb::ndim<2>, nb::c_contig, nb::device::cpu> x,
        unsigned long quality) {
    const size_t ilen = x.shape(0);
    const size_t olen = ilen * out_rate / in_rate + 1;
    unsigned channels = x.shape(1);

    const soxr_datatype_t ntype = to_soxr_datatype(typeid(T));

    // make soxr config
    soxr_error_t err = NULL;
    const soxr_io_spec_t io_spec = soxr_io_spec(ntype, ntype);
    const soxr_quality_spec_t quality_spec = soxr_quality_spec(quality, 0);

    size_t odone = 0;
    T *y = new T[olen * channels] { 0 };

    err = soxr_oneshot(
        in_rate, out_rate, channels,
        x.data(), ilen, NULL,
        y, olen, &odone,
        &io_spec, &quality_spec, NULL);

    if (err != NULL) {
        throw std::runtime_error(err);
    }

    // Delete 'y' when the 'owner' capsule expires
    nb::capsule owner(y, [](void *p) noexcept {
       delete[] (T *) p;
    });
    return nb::ndarray<nb::numpy, T>(y, { odone, channels }, owner);
}


NB_MODULE(soxr_ext, m) {
    m.def("add", [](int a, int b) { return a + b; }, "a"_a, "b"_a);

    m.def("version", soxr_version);

    nb::class_<CySoxr>(m, "CySoxr")
        .def(nb::init<double, double, unsigned, soxr_datatype_t, unsigned long>())
        .def("process_float32", &CySoxr::process<float>)
        .def("process_float64", &CySoxr::process<double>)
        .def("process_int32", &CySoxr::process<int32_t>)
        .def("process_int16", &CySoxr::process<int16_t>);

    m.def("cysoxr_divide_proc_float32", cysoxr_divide_proc<float>);
    m.def("cysoxr_divide_proc_float64", cysoxr_divide_proc<double>);
    m.def("cysoxr_divide_proc_int32", cysoxr_divide_proc<int32_t>);
    m.def("cysoxr_divide_proc_int16", cysoxr_divide_proc<int16_t>);

    m.def("cysoxr_oneshot_float32", cysoxr_oneshot<float>);
    m.def("cysoxr_oneshot_float64", cysoxr_oneshot<double>);
    m.def("cysoxr_oneshot_int32", cysoxr_oneshot<int32_t>);
    m.def("cysoxr_oneshot_int16", cysoxr_oneshot<int16_t>);

    nb::enum_<soxr_datatype_t>(m, "soxr_datatype_t")
        .value("SOXR_FLOAT32_I", SOXR_FLOAT32_I)
        .value("SOXR_FLOAT64_I", SOXR_FLOAT64_I)
        .value("SOXR_INT32_I", SOXR_INT32_I)
        .value("SOXR_INT16_I", SOXR_INT16_I)
        .export_values();
    
    m.attr("QQ") = SOXR_QQ;
    m.attr("LQ") = SOXR_LQ;
    m.attr("MQ") = SOXR_MQ;
    m.attr("HQ") = SOXR_HQ;
    m.attr("VHQ") = SOXR_VHQ;
}