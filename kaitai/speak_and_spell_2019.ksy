meta:
  id: speak_and_spell_2019
  title: "Speak and Spell Flash Memory"
  endian: be
  bit-endian: be
types:
  ote_ptr:
    seq:
      - id: pointer
        type: b24
  speech_ptr:
    seq:
      - id: pointer
        type: b24
        doc: "A pointer to an address in flash."
  offset_table_entry:
    seq:
      - id: playback_rate
        type: u2
        doc: "Playback rate (higher value means slower playback).  Usually 0xCD but the last one is 0xAB"
      - id: speech_data
        type: speech_ptr
  speech_frame:
    seq:
      - id: frame_data
        size: 12
  speech_data:
    params:
      - id: i
        type: u4
    instances:
      body:
        pos: _root.offset_table[i].speech_data.pointer
        type: speech_frame
        repeat: until
        repeat-until: ( _.frame_data[0] % 2 ) == 0 and _index > 1
        #repeat-until: '( _.frame_header & 0x1 ) == 0'
        # had to use the syntax above because (_.frame_header & 1) == 0 gets the parentheses removed and then the logic doesn't work

      
seq:
  - id: num_offset_table_entries
    type: u2
    doc: "Number of entries in offset table"
  - id: offset_table_start_addr
    type: ote_ptr
    doc: "Address of first entry in offset table"
  - id: offset_table_end_addr
    type: ote_ptr
    doc: "Address of one byte past the last entry in offset table"
instances:
    offset_table:
      type: offset_table_entry
      repeat: expr
      repeat-expr: num_offset_table_entries
      pos: offset_table_start_addr.pointer
    speeches:
      type: speech_data(_index)
      repeat: expr
      repeat-expr: num_offset_table_entries
      

    
  
    
  