# Validation and DTOs

Load when writing request or response DTOs, configuring the global pipe, handling query parameters, or documenting endpoints.

If the project validates with Zod (a `ZodValidationPipe`, `nestjs-zod`) instead of `class-validator`, keep Zod and apply the same rules: one schema per request shape, strip unknown keys, coerce explicitly, infer the type from the schema.

## Global pipe

Register once, as `APP_PIPE` or in `main.ts`:

| Option | Value | Why |
|---|---|---|
| `whitelist` | `true` | Drops properties with no decorator |
| `forbidNonWhitelisted` | `true` | Rejects them instead, so a typo in a client field name surfaces as 400 rather than silently ignored |
| `transform` | `true` | Payload becomes a DTO instance; `@Type()` conversions run |
| `transformOptions.enableImplicitConversion` | leave `false` | Implicit conversion turns `"false"` into `true`; convert explicitly with `@Type(() => Number)` / a `@Transform` |
| `stopAtFirstError` | project choice | `false` returns every field error at once, which clients usually want |

Use a custom `exceptionFactory` only to reshape errors into the project's envelope; usually the global filter does that already.

## Request DTO rules

- One class per operation: `CreateOrderDto`, `UpdateOrderDto`, `ListOrdersQueryDto`. Never reuse the entity.
- Every property carries at least one validator; optional ones carry `@IsOptional()` **plus** their type validator.
- Derive update DTOs: `PartialType(CreateOrderDto)`, `PickType`, `OmitType`, `IntersectionType` — from `@nestjs/swagger` if Swagger is used (keeps docs), else `@nestjs/mapped-types`.
- Nested objects: `@ValidateNested()` + `@Type(() => ChildDto)`; arrays add `{ each: true }` and `@ArrayMaxSize(n)`.
- Bound every string and array: `@MaxLength`, `@ArrayMaxSize`. Unbounded input is a cheap denial-of-service.
- Enums: `@IsEnum(OrderStatus)`; ids: `@IsUUID()` or a param pipe.
- Do not accept server-owned fields (`id`, `createdAt`, `ownerId`, `role`, `isAdmin`) in create/update DTOs. The owner comes from the authenticated user, not the body.
- Mark properties `readonly` or with `!` definite assignment consistently with the project.

## Query parameters

Query strings arrive as strings. In a query DTO:

- Numbers: `@Type(() => Number) @IsInt() @Min(1) @Max(100) limit = 20;`
- Booleans: an explicit `@Transform(({ value }) => value === 'true')` — never `Boolean(value)`.
- Defaults as property initializers so the service never sees `undefined` for paging.
- Sort fields: validate against an allow-list (`@IsIn(['createdAt', '-createdAt'])`) before they reach the repository.

## Route params

Use built-in pipes rather than DTOs for single params: `ParseUUIDPipe`, `ParseIntPipe`, `ParseEnumPipe`. A malformed id then fails as 400 before the service runs.

## Response DTOs

- The controller returns a response DTO, never an entity. Two accepted styles; keep whichever the project uses:
  - **Explicit mapping** — `static from(entity): OrderResponseDto` listing each field. Most explicit; no reflection.
  - **Serializer** — `ClassSerializerInterceptor` with `@Exclude()` by default and `@Expose()` per field. Fragile when the entity is a plain object instead of a class instance.
- Lists return the collection under a key with paging metadata, not a bare array, so pagination can be added without a breaking change.
- Dates go out as ISO-8601 strings; money as integer minor units or a decimal string, never a float.

## OpenAPI

When `@nestjs/swagger` is installed:

- Prefer the Swagger CLI plugin (in `nest-cli.json`) over hand-written `@ApiProperty()` on every field — fewer lines, docs follow the types.
- Document error responses (`@ApiNotFoundResponse()`, etc.) with the shared error envelope type.
- Group by `@ApiTags(feature)`; secure routes with `@ApiBearerAuth()`.

Do not install Swagger to satisfy this list; ask first.

## Checks

- Search for DTO properties with no decorator: a class in `dto/` where a property line is not preceded by a decorator line.
- Search controllers for `@Body() body: any`, `@Body() body: Record<...>`, `@Query() q: any` — each is an unvalidated input.
- Search controller return types for entity classes.
