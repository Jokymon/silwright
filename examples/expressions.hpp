#pragma once

#include <memory>
#include <string>
#include <variant>

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

}  // namespace expressions
