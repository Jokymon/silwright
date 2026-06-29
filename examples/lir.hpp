#pragma once

#include <memory>
#include <string>
#include <variant>
#include <vector>

namespace lir {

struct number;
struct char_literal;
struct bool_literal;
struct string_literal;
struct if_expression;
struct unary_expression;

using expr = std::variant<number, char_literal, bool_literal, string_literal, if_expression, unary_expression>;

struct number {
    long long number;
    type_id assigned_type;
};
struct char_literal {
    uint32_t ch;
};
struct bool_literal {
    bool value;
};
struct string_literal {
    size_t table_index;
    long long size;
};
struct if_expression {
    std::unique_ptr<expr> condition;
    std::vector<std::unique_ptr<expr>> then_code;
    std::vector<std::unique_ptr<expr>> else_code;
    type_id assigned_type;
};
struct unary_expression {
    std::unique_ptr<expr> expr;
    type_id assigned_type;
};

}  // namespace lir
