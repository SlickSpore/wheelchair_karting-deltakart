#include <iostream>
#include <vector>
#include <numeric>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <opencv2/opencv.hpp>
#include <opencv2/aruco.hpp>

namespace py = pybind11;

class HeadsetRun {
    private:
    cv::Point center;
    cv::Point2f headset_position;
    cv::VideoCapture cap;
    cv::Mat k, d, undistorted, distorted, map1, map2;
    cv::aruco::Dictionary aruco_dict;
    cv::aruco::DetectorParameters parameters;
    cv::aruco::ArucoDetector detector;

    std::vector<std::vector<cv::Point2f>> marker_coords, rejected_markers;
    std::vector<int> marker_ids;

    cv::Point2f get_marker_center(const std::vector<cv::Point2f>& corners) {
        cv::Point2f center(0,0);

        for (auto &p : corners)
            center += p;

        center *= 1.0f / corners.size();

        return center;
    }

    public:

    HeadsetRun() : cap(0) {}

    ~HeadsetRun(){
        cap.release();
        cv::destroyAllWindows();
    }

    int connect_camera(){
        /* Load Camera Parameters and Init Markers */
        cv::FileStorage fs("camera_distortion.yaml", cv::FileStorage::READ);

        fs["K"] >> k;
        fs["D"] >> d;

        aruco_dict = cv::aruco::getPredefinedDictionary(cv::aruco::DICT_4X4_100);
        detector = cv::aruco::ArucoDetector(aruco_dict, parameters);
                  
        /* Init Video capture device */
        cap >> distorted;

        cv::initUndistortRectifyMap(
            k, d,
            cv::Mat(),
            k,
            distorted.size(),
            CV_16SC2,
            map1,
            map2
        );

        center = cv::Point(distorted.cols/2, distorted.rows/2);

        if (!cap.isOpened() || !fs.isOpened()) {
            std::cerr << "Failed to open camera or to read camera_distortion.yaml\n";
            return -1;
        }

        return 0;
    }

    std::vector<float> get_headset_position() {

        marker_coords.clear();
        marker_ids.clear();
        rejected_markers.clear();

        cap >> distorted;

        if (distorted.empty()) {
            return std::vector<float>{-1, -1};
        }

        cv::remap(distorted, undistorted, map1, map2, cv::INTER_LINEAR);

        if (undistorted.empty())
            return std::vector<float>{-1, -1};

        detector.detectMarkers(undistorted, marker_coords, marker_ids, rejected_markers);

        if (!marker_ids.empty()){
            headset_position = get_marker_center(marker_coords[0]);
        }
        
        return std::vector<float>{headset_position.x, headset_position.y};
    }
};

PYBIND11_MODULE(HeadsetRun, m) {
    py::class_<HeadsetRun>(m, "HeadsetRun")
        .def(py::init<>())
        .def("get_headset_position",
             &HeadsetRun::get_headset_position,
             py::call_guard<py::gil_scoped_release>())
        .def("connect_camera",
             &HeadsetRun::connect_camera);
}