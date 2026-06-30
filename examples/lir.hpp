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
struct function_parameter;
struct function_signature;
struct function_head;
struct function_definition;

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
struct function_parameter {
    std::string name;
};
struct function_signature {
    std::vector<function_parameter> parameters;
    type_id function_type;
};
struct function_head {
    std::string name;
    function_signature signature;
};
struct function_definition {
    std::unique_ptr<function_head> function_head;
    std::vector<std::unique_ptr<expr>> code;
};

}  // namespace lir
