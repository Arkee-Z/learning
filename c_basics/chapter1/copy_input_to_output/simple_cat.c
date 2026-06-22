#define COPY_INPUT_TO_OUTPUT_IMPLEMENTATION
#include "copy_input_to_output.h"

int main(int argc, char *argv[]) {

    if(argc == 1) {

        // 无参数: 标准输入 -> 输出
        return copy_stream(stdin, stdout, 0);
    }

    int ret = 0;
    for (int i = 1; i < argc; i++) {

        FILE *fp = fopen(argv[i], "rb");
        if (!fp) {

            fprintf(stderr, "simple_cat: %s: No such file or directory\n", argv[i]);
            ret = 1;
            continue;
        }

        // copy stream to stdout
        if (copy_stream(fp, stdout, 0) != 0) {

            fprintf(stderr, "simple_cat: %s: Read error\n", argv[i]);
            ret = 1;
        }
        fclose(fp);
    }
    return ret;
}