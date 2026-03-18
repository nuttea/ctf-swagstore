Setup need to be done in Datadog Temp Org


LOGS
- add facet for service productcatalog - Path @ID for CTF #9
- Sensitive Data Protection - enable SDP and add Visa Card obfuscation rule
- checkoutservice create Log Pipeline parser to extrace email
  ```
  autoFilledRule1 order\s+confirmation\s+email\s+sent\s+to\s+\"%{notSpace:email}"\s+dd\.trace_id\=%{integer}
  ```
0