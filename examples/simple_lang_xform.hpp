#pragma once
#include "simple_lang_transformer.hpp"

class simple_lang_xform : public lir::transformer
{
protected:
    lir::expr_list visit_multiple(lir::store_record_expression& value) override;
};