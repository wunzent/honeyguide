// start/validator.ts
//
// This file is a preload file — it runs when the application boots.
// Generate it with:  node ace make:preload validator
//
// It configures global custom validation messages and the error reporter
// for the entire AdonisJS application.

import vine, { SimpleMessagesProvider } from '@vinejs/vine'
import { JSONAPIErrorReporter } from '#validation/reporters/json_api_error_reporter'

// ---------------------------------------------------------------------------
// Custom error messages
// ---------------------------------------------------------------------------

const messages: Record<string, string> = {
  // ---- Generic rule messages (apply to all fields) ----
  'required': 'The {{ field }} field is required',
  'string': 'The {{ field }} field must be a string',
  'number': 'The {{ field }} field must be a number',
  'boolean': 'The {{ field }} field must be true or false',
  'date': 'The {{ field }} field must be a valid date',
  'email': 'Please provide a valid email address',
  'url': 'The {{ field }} field must be a valid URL',
  'minLength': 'The {{ field }} field must be at least {{ min }} characters',
  'maxLength': 'The {{ field }} field must not exceed {{ max }} characters',
  'fixedLength': 'The {{ field }} field must be exactly {{ size }} characters',
  'min': 'The {{ field }} field must be at least {{ min }}',
  'max': 'The {{ field }} field must not exceed {{ max }}',
  'confirmed': 'The {{ field }} confirmation does not match',
  'enum': 'The selected {{ field }} is not valid',
  'accepted': 'The {{ field }} field must be accepted',
  'regex': 'The {{ field }} field format is invalid',
  'unique': 'The {{ field }} has already been taken',
  'exists': 'The selected {{ field }} does not exist',

  // ---- Field-specific overrides ----
  'username.required': 'Please choose a username',
  'username.minLength': 'Username must be at least {{ min }} characters',
  'email.required': 'Email address is required',
  'password.required': 'Password is required',
  'password.minLength': 'Password must be at least {{ min }} characters',
  'password.confirmed': 'Password and confirmation do not match',

  // ---- Nested / array fields ----
  'profile.bio.maxLength': 'Bio must not exceed {{ max }} characters',
  'contacts.*.email.required': 'Each contact must have an email address',
  'contacts.*.email.email': 'Each contact email must be valid',
  'tags.*.string': 'Each tag must be a string',
}

// ---------------------------------------------------------------------------
// Human-readable field name substitutions
// ---------------------------------------------------------------------------

const fields: Record<string, string> = {
  first_name: 'first name',
  last_name: 'last name',
  phone_number: 'phone number',
  dob: 'date of birth',
  created_at: 'creation date',
  updated_at: 'update date',
}

// ---------------------------------------------------------------------------
// Register globally
// ---------------------------------------------------------------------------

vine.messagesProvider = new SimpleMessagesProvider(messages, fields)

// Uncomment to use a custom error reporter globally:
// vine.errorReporter = () => new JSONAPIErrorReporter()
