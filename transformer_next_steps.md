These are some notes regarding the sketch of a transformation language for trees:

- Do not add any explicit target coverage declarations but rather have this as
  a validation
- We currently have a mix of 'emit' based returning combined with plain
  constructors in a 'rule'
- The target in a 'rule' seems to appear twice, once after 'to' and a second time after the '=' sign where a new "instance" is created
- If the field type is not a builtin type but a "mapped" type, then we assume that it can be copied by value and we can just assign it
- Different namespace notation? Somehow I feel like I would prefer the ':' notation for specifying the module of the transformation
- For converting into a Place we current use two helpers where I would prefer no helpers but instead introduce something that might allow some form of functional manipulation/construction of the new projection field value

- A big challenge might be the need for some helper functions like how to get the type of a symbol, getting the index of a field for a record or getting the type of a field in a record




---> We have to get the BinaryOp in the AST also into the NDEF definitions to work better with transformations

