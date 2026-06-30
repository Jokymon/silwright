#include "simple_lang.hpp"
#include "simple_lang_dump.hpp"

#include <iostream>
#include <memory>
#include <utility>

namespace {

struct dump_context {};

template <class Node>
std::unique_ptr<expressions::expr> make_expression(Node node) {
    return std::make_unique<expressions::expr>(std::move(node));
}

}  // namespace

int main() {
    using namespace expressions;

    function_definition function{
        .head = function_head{
            .name = "calculate",
            .signature = function_signature{
                .return_type = "number",
                .parameter_types = {"number", "number"},
            },
        },
        .code = {},
    };

    function.code.push_back(make_expression(variable{.name = "left"}));
    function.code.push_back(make_expression(number{.value = 42}));
    function.code.push_back(make_expression(binary_expression{
        .op = op_t::Add,
        .left = make_expression(variable{.name = "left"}),
        .right = make_expression(number{.value = 1}),
    }));

    dump_context context;
    dump(std::cout, context, function);
}
