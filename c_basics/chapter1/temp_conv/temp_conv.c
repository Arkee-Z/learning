#include <stdio.h>
#include <stdbool.h>

typedef enum {
    F2C,
    C2F
} Converter;

float F2C_converter(float fahr) {

    float celsius;
    celsius = (5.0 / 9.0) * (fahr - 32.0);

    return celsius;
}

float C2F_converter(float celsius) {

    float fahr;
    fahr = celsius * (9.0 / 5.0) + 32.0;

    return fahr;
}

void print_temp_mapping_table(int lower, int upper, int step, Converter converter, bool is_reverse) {

    float temp_fahr, temp_celsius;
    int temp_lower, temp_upper, temp_step;

    temp_lower = lower; 
    temp_upper = upper;
    temp_step = step;

    // temp_fahr = (float)temp_lower;

    char *F2C_title = "Fahr-Celsius";
    char *C2F_title = "Celsius-Fahr";
    printf("------------\n");

    // while (temp_fahr <= temp_upper) {

    //     temp_celsius = F2C_converter(temp_fahr);
    //     printf(" %4.0f %6.1f\n", temp_fahr, temp_celsius);
    //     temp_fahr = temp_fahr + (float)temp_step;
    // }
    switch (converter) {

        case F2C:
            printf("%s\n", F2C_title);
            printf("------------\n");
            if (is_reverse) {

                for (temp_fahr = temp_upper; 
                    temp_fahr >= temp_lower;
                    temp_fahr = temp_fahr - temp_step) {

                    temp_celsius = F2C_converter(temp_fahr);
                    printf("%4.0f %6.1f\n", temp_fahr, temp_celsius);
                }
            } else {

                for (temp_fahr = temp_lower; 
                    temp_fahr <= temp_upper;
                    temp_fahr = temp_fahr + temp_step) {

                    temp_celsius = F2C_converter(temp_fahr);
                    printf("%4.0f %6.1f\n", temp_fahr, temp_celsius);
                }
            }
            break;
        case C2F:
            printf("%s\n", C2F_title);
            printf("------------\n");
            if (is_reverse) {

                for (temp_celsius = temp_upper; 
                    temp_celsius >= temp_lower;
                    temp_celsius = temp_celsius - temp_step) {

                    temp_fahr = C2F_converter(temp_celsius);
                    printf("%4.0f %6.1f\n", temp_celsius, temp_fahr);
                }
            } else {

                for (temp_celsius = temp_lower; 
                    temp_celsius <= temp_upper;
                    temp_celsius = temp_celsius + temp_step) {

                    temp_fahr = C2F_converter(temp_celsius);
                    printf("%4.0f %6.1f\n", temp_celsius, temp_fahr);
                }
            }
            break;
        default:
            printf("ERROR: invalid converter!");
            break;
    } 

    printf("------------\n");
}

// void test_f2c() {

//     int f2c_lower, f2c_upper, f2c_step;

//     f2c_lower = 0;
//     f2c_upper = 300;
//     f2c_step = 20;

//     // print_temp_mapping_table(0, 100, 1, C2F, true);
//     print_temp_mapping_table(f2c_lower, f2c_upper, f2c_step, F2C, true);
// }

// void test_c2f() {
//     int c2f_lower, c2f_upper, c2f_step;

//     c2f_lower = 0;
//     c2f_upper = 100;
//     c2f_step = 1;

//     print_temp_mapping_table(c2f_lower, c2f_upper, c2f_step, C2F, false);
// }

// int main(void) {

//     test_f2c();
//     test_c2f();
// }