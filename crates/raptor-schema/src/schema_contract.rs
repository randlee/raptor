//! Structural JSON Schema policy for canonical records.
use schemars::schema::{RootSchema, Schema, SchemaObject, SingleOrVec};

fn visit(schema: &mut Schema) {
    if let Schema::Object(object) = schema {
        visit_object(object);
    }
}

fn visit_object(schema: &mut SchemaObject) {
    if let Some(object) = &mut schema.object {
        object.required = object.properties.keys().cloned().collect();
        object.additional_properties = Some(Box::new(Schema::Bool(false)));
        for property in object.properties.values_mut() {
            visit(property);
        }
    }
    if let Some(array) = &mut schema.array
        && let Some(items) = &mut array.items
    {
        match items {
            SingleOrVec::Single(item) => visit(item),
            SingleOrVec::Vec(items) => items.iter_mut().for_each(visit),
        }
    }
    if let Some(subschemas) = &mut schema.subschemas {
        for list in [
            &mut subschemas.all_of,
            &mut subschemas.any_of,
            &mut subschemas.one_of,
        ]
        .into_iter()
        .flatten()
        {
            list.iter_mut().for_each(visit);
        }
        for child in [
            &mut subschemas.not,
            &mut subschemas.if_schema,
            &mut subschemas.then_schema,
            &mut subschemas.else_schema,
        ]
        .into_iter()
        .flatten()
        {
            visit(child);
        }
    }
}

pub(crate) fn apply(schema: &mut RootSchema) {
    visit_object(&mut schema.schema);
    for (name, definition) in &mut schema.definitions {
        visit(definition);
        if crate::schema::ScalarKind::parse(name).is_some()
            && let Schema::Object(object) = definition
        {
            let metadata = object.metadata.get_or_insert_with(Default::default);
            metadata.description = Some(
                "Structural string; validate_scalar and accept enforce canonical scalar rules."
                    .into(),
            );
        }
    }
}
