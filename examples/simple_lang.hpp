#pragma once

#include <memory>
#include <optional>
#include <string>
#include <variant>
#include <vector>
#include <cstddef>
#include <cstdint>
#include "symbol.hpp"

namespace expressions {

enum class binary_op_t {
    Multiply,
    Division,
    Modulus,
    Plus,
    Minus,
    Equals,
    NotEquals,
    LessThan,
    LessThanEqual,
    GreaterThan,
    GreaterThanEqual,
    AndOp,
    OrOp,
    Shl,
    Shr
};

struct base_var;
struct deref;
struct field;
struct place;
struct number;
struct char_literal;
struct bool_literal;
struct string_literal;
struct allocate_record_expression;
struct field_initialisation;
struct store_record_expression;
struct load_expression;
struct store_expression;
struct if_expression;
struct while_expression;
struct function_call;
struct cast_expression;
struct discard_expression;
struct return_expression;
struct break_statement;
struct unary_expression;
struct binary_expression;
struct function_signature;
struct function_head;
struct function_definition;
struct import_definition;
struct global_definition;
struct module;

using place_elem = std::variant<deref, field>;
using expr = std::variant<number, char_literal, bool_literal, string_literal, allocate_record_expression, store_record_expression, load_expression, store_expression, if_expression, while_expression, function_call, cast_expression, discard_expression, return_expression, break_statement, unary_expression, binary_expression>;

struct base_var {
    std::string name;
    symbol_id symbol_ref;
};
struct deref {

};
struct field {
    std::size_t index;
};
struct place {
    base_var base;
    std::vector<place_elem> projection;
};
struct number {
    long long value;
};
struct char_literal {
    std::uint32_t ch;
};
struct bool_literal {
    bool value;
};
struct string_literal {
    std::size_t table_index;
    long long size;
};
struct allocate_record_expression {
    type_id type;
};
struct field_initialisation {
    std::size_t field_index;
    std::unique_ptr<expr> value;
};
struct store_record_expression {
    std::vector<field_initialisation> initialisations;
    type_id stored_type;
};
struct load_expression {
    place source;
    type_id assigned_type;
};
struct store_expression {
    place target;
    std::unique_ptr<expr> value;
    type_id stored_type;
};
struct if_expression {
    std::unique_ptr<expr> condition;
    std::vector<std::unique_ptr<expr>> then_code;
    std::vector<std::unique_ptr<expr>> else_code;
    type_id assigned_type;
};
struct while_expression {
    std::unique_ptr<expr> condition;
    std::vector<std::unique_ptr<expr>> while_code;
};
struct function_call {
    std::string function_name;
    symbol_id symbol_ref;
    std::vector<std::unique_ptr<expr>> arguments;
};
struct cast_expression {
    std::unique_ptr<expr> expression;
    type_id cast_type;
};
struct discard_expression {
    std::unique_ptr<expr> expression;
};
struct return_expression {
    std::unique_ptr<expr> expression;
    bool is_explicit;
};
struct break_statement {

};
struct unary_expression {
    std::unique_ptr<expr> expr;
    type_id assigned_type;
};
struct binary_expression {
    binary_op_t op;
    std::unique_ptr<expr> left;
    std::unique_ptr<expr> right;
    type_id assigned_type;
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
struct import_definition {
    std::string ns_name;
    std::unique_ptr<function_head> function_head;
    std::optional<std::string> alias;
};
struct global_definition {
    std::string name;
    type_id assigned_type;
    symbol_id symbol_ref;
    long long init_value;
};
struct module {
    std::vector<std::unique_ptr<import_definition>> imports;
    std::vector<std::unique_ptr<global_definition>> globals;
    std::vector<std::unique_ptr<function_definition>> functions;
};

}  // namespace expressions
