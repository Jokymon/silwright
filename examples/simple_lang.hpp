#pragma once

#include <memory>
#include <string>
#include <variant>
#include <vector>

namespace expressions {

enum class op_t {
    Add,
    Subtract,
    Multiply,
    Divide,
    Modulus
};

struct variable;
struct number;
struct binary_expression;
struct function_signature;
struct function_head;
struct function_definition;

using expr = std::variant<variable, number, binary_expression>;

struct variable {
    std::string name;
};
struct number {
    long long value;
};
struct binary_expression {
    op_t op;
    std::unique_ptr<expr> left;
    std::unique_ptr<expr> right;
};
struct function_signature {
    std::string return_type;
    std::vector<std::string> parameter_types;
};
struct function_head {
    std::string name;
    function_signature signature;
};
struct function_definition {
    function_head head;
    std::vector<std::unique_ptr<expr>> code;
};

}  // namespace expressions
