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
struct function_definition;

using expr = std::variant<variable, number, binary_expression>;

struct variable {
    std::string name;
};
struct number {
    long value;
};
struct binary_expression {
    op_t op;
    std::unique_ptr<expr> left;
    std::unique_ptr<expr> right;
};
struct function_definition {
    std::vector<std::unique_ptr<expr>> code;
};

}  // namespace expressions
