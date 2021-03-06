cmake_minimum_required(VERSION 3.0)

add_executable(compute-stft-stats compute-stft-stats.cc)
add_executable(compute-masks compute-masks.cc)
add_executable(compute-srp-phat compute-srp-phat.cc)
add_executable(wav-separate wav-separate.cc)
add_executable(wav-estimate wav-estimate.cc)
add_executable(rir-simulate rir-simulate.cc)
add_executable(apply-fixed-beamformer apply-fixed-beamformer.cc)
add_executable(apply-supervised-mvdr apply-supervised-mvdr.cc)
add_executable(apply-supervised-max-snr apply-supervised-max-snr.cc)
add_executable(matrix-scale-elements matrix-scale-elements.cc)
add_executable(matrix-scale-rows matrix-scale-rows.cc)

target_link_libraries(compute-stft-stats ${DEPEND_LIBS} setk)
target_link_libraries(compute-masks ${DEPEND_LIBS} setk)
target_link_libraries(compute-srp-phat ${DEPEND_LIBS} setk)
target_link_libraries(wav-separate ${DEPEND_LIBS} setk)
target_link_libraries(wav-estimate ${DEPEND_LIBS} setk)
target_link_libraries(rir-simulate ${DEPEND_LIBS} setk)
target_link_libraries(apply-fixed-beamformer ${DEPEND_LIBS} setk)
target_link_libraries(apply-supervised-mvdr ${DEPEND_LIBS} setk)
target_link_libraries(apply-supervised-max-snr ${DEPEND_LIBS} setk)
target_link_libraries(matrix-scale-elements ${DEPEND_LIBS} setk)
target_link_libraries(matrix-scale-rows ${DEPEND_LIBS} setk)
