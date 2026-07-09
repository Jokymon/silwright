#include "simple_lang.hpp"
#include "simple_lang_dump.hpp"
#include "simple_lang_xform.hpp"
#include <iostream>
#include <memory>
#include <utility>

namespace {

struct dump_context {
    std::vector<std::string> type_names;
    std::vector<std::string> symbol_names;
};

template <class Node>
std::unique_ptr<lir::expr> make_expression(Node node) {
    return std::make_unique<lir::expr>(std::move(node));
}

}  // namespace

// This overload is found through argument-dependent lookup because type_id is an argument.
// It demonstrates how an application-defined scalar uses the generic dump context.
void dump_value(std::ostream& out, dump_context& context, const type_id& value) {
    out << context.type_names.at(value.index);
}

void dump_value(std::ostream& out, dump_context& context, const symbol_id& value) {
    out << context.symbol_names.at(value.index);
}

void dump_value(std::ostream& out, dump_context& context, const function_signature& value) {
    out << "function sig";
}

int main() {
    using namespace lir;

    function_definition function{
        .head = function_head{
            .name = "calculate",
            .signature = function_signature{
                .parameters = {function_parameter{"boolean"}, {"number"}},
                .function_type = type_id{0},
            },
        },
        .code = {},
    };

    function.code.push_back(make_expression(bool_literal{.value = true}));
    function.code.push_back(make_expression(number{.value = 42}));
    function.code.push_back(make_expression(char_literal{.ch = '!'}));
    auto sre = store_record_expression{
        .target = place{ .base = base_var{}, .projection = {}},
        .initialisations = {}, 
        .stored_type = type_id{0}
    };
    sre.initialisations.push_back(field_initialisation{
                .field_index = 0,
                .value = make_expression(number{.value = 2})
            });
    sre.initialisations.push_back(field_initialisation{
                .field_index = 2,
                .value = make_expression(char_literal{.ch = '@'})
            });
    function.code.push_back(make_expression(std::move(sre)));
    function.code.push_back(
        make_expression(string_literal{.table_index = 3, .size = 12}));
    function.code.push_back(make_expression(allocate_record_expression{.type = type_id{0}}));
    function.code.push_back(make_expression(binary_expression{
        .op = binary_op_t::Multiply,
        .left = make_expression(number{.value = 6}),
        .right = make_expression(number{.value = 7}),
    }));
    auto fct = std::make_unique<lir::function_definition>(std::move(function));

    simple_lang_xform xformer;
    auto new_fcts = xformer.rewrite(std::move(fct));

    dump_context context{
        .type_names = {"example_record"},
        .symbol_names = {"example_symbol"},
    };
    dump(std::cout, context, *new_fcts[0]);
}
