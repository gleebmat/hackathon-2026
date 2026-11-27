/* Replacement for proj_cm55/source/inference_task.c in Infineon's mtb-example-psoc-edge-ml-aihub-deploy-vision.
 * The precompiled person-segmentation pipeline turns the USER LED on while a person is detected and exposes no
 * result API, so after each frame we sample the LED pin and print one presence line per second over UART:
 *     PRESENCE <0|1> <frames_with_person>/<frames>
 * bridge/bridge.py parses these lines. Original logic is unchanged. */
#include <stdio.h>
#include "cybsp.h"
#include "FreeRTOS.h"
#include "task.h"
#include "pipeline.h"

void ml_pipeline_task(void *arg)
{
    uint32_t frames = 0, person_frames = 0;
    TickType_t window_start = xTaskGetTickCount();

    ml_pipeline_model_init();
    while (1) {
        getData();
        ml_pipeline_preprocess();
        ml_pipeline_inference();
        ml_pipeline_post_process();

        frames++;
        if (Cy_GPIO_ReadOut(CYBSP_USER_LED_PORT, CYBSP_USER_LED_PIN)) {
            person_frames++;
        }
        if ((xTaskGetTickCount() - window_start) >= pdMS_TO_TICKS(1000)) {
            printf("PRESENCE %d %lu/%lu\r\n", person_frames * 2 >= frames ? 1 : 0,
                   (unsigned long)person_frames, (unsigned long)frames);
            frames = person_frames = 0;
            window_start = xTaskGetTickCount();
        }
    }
}
