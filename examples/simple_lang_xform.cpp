#include "simple_lang_xform.hpp"

template <class Node>
std::unique_ptr<lir::expr> make_expression(Node node) {
    return std::make_unique<lir::expr>(std::move(node));
}

lir::expr_list simple_lang_xform::visit_multiple(lir::store_record_expression& value)
{
    lir::expr_list out;
    for (auto& init : value.initialisations)
    {
        std::vector<lir::place_elem> projs;
        projs.push_back(lir::field{init.field_index});
        out.push_back(make_expression(lir::store_expression{
            .target = lir::place{
                .base = lir::base_var{},
                .projection = std::move(projs)
            },
            .value = std::move(init.value),
            .stored_type = type_id{0}
        }));
    }

    return out;
}
