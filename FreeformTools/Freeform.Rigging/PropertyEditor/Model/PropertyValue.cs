/*
 * Freeform Rigging and Animation Tools
 * Copyright (C) 2020  Micah Zahm
 *
 * Freeform Rigging and Animation Tools is free software: you can redistribute it 
 * and/or modify it under the terms of the GNU General Public License as published 
 * by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Freeform Rigging and Animation Tools is distributed in the hope that it will 
 * be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Freeform Rigging and Animation Tools.  
 * If not, see <https://www.gnu.org/licenses/>.
 */

namespace Freeform.Rigging.PropertyEditor
{
  using System;
  using System.Collections.Generic;
  using System.ComponentModel;
  using System.Linq;
  using System.Text;
  using System.Threading.Tasks;

  public class PropertyValue : INotifyPropertyChanged
  {
    public event EventHandler AttributeChangedHandler;

    public string NodePath;

    string _name;
    public string Name
    {
      get { return _name; }
      set
      {
        _name = value;
        RaisePropertyChanged("Name");
      }
    }

    string _value;
    public string Value
    {
      get { return _value; }
      set
      {
        _value = value;

        AttributeStringEventArgs eventArgs = new AttributeStringEventArgs()
        {
          NodeName = NodePath,
          Attribute = Name,
          Value = _value
        };
        AttributeChangedHandler?.Invoke(this, eventArgs);

        RaisePropertyChanged("Value");
      }
    }

    string _gridStyle;
    public string GridStyle
    {
      get { return _gridStyle; }
      set
      {
        _gridStyle = value;
        RaisePropertyChanged("GridStyle");
      }
    }

    bool _readOnly;
    public bool ReadOnly
    {
      get { return _readOnly; }
      set
      {
        _readOnly = value;
        GridStyle = value ? "DisabledGrid" : "SubGrid";
        RaisePropertyChanged("ReadOnly");
      }
    }

    public PropertyValue(string name, string nodePath)
    {
      GridStyle = "SubGrid";
      ReadOnly = false;
      Name = name;
      NodePath = nodePath;
    }

    public PropertyValue(string name, string value, string nodePath)
    {
      GridStyle = "SubGrid";
      ReadOnly = false;
      Name = name;
      Value = value;
      NodePath = nodePath;
    }


    public class AttributeStringEventArgs : EventArgs
    {
      public string NodeName = "";
      public string Attribute = "";
      public string Type = "string";
      public string Value = "";
    }


    protected void RaisePropertyChanged(string prop)
    {
      PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
    }
    public event PropertyChangedEventHandler PropertyChanged;
  }

  public class StringValue : PropertyValue
  {
    public StringValue(string name, string value, string nodePath) : base(name, nodePath)
    {
      Value = value;
    }
  }

  public class IntValue : PropertyValue
  {
    public new event EventHandler AttributeChangedHandler;

    int _value;
    public new int Value
    {
      get { return _value; }
      set
      {
        _value = value;

        AttributeIntEventArgs eventArgs = new AttributeIntEventArgs()
        {
          NodeName = NodePath,
          Attribute = Name,
          Value = _value
        };
        AttributeChangedHandler?.Invoke(this, eventArgs);

        RaisePropertyChanged("Value");
      }
    }

    public IntValue(string name, int value, string nodePath) : base(name, nodePath)
    {
      Value = value;
    }

    public class AttributeIntEventArgs : EventArgs
    {
      public string Guid = "";
      public string NodeName = "";
      public string Attribute = "";
      public string Type = "short";
      public int Value = 0;
    }
  }

  public class FloatValue : PropertyValue
  {
    public new event EventHandler AttributeChangedHandler;

    float _value;
    public new float Value
    {
      get { return _value; }
      set
      {
        _value = value;

        AttributeFloatEventArgs eventArgs = new AttributeFloatEventArgs()
        {
          NodeName = NodePath,
          Attribute = Name,
          Value = _value
        };
        AttributeChangedHandler?.Invoke(this, eventArgs);

        RaisePropertyChanged("Value");
      }
    }

    public FloatValue(string name, float value, string nodePath) : base(name, nodePath)
    {
      Value = value;
    }

    public class AttributeFloatEventArgs : EventArgs
    {
      public string Guid = "";
      public string NodeName = "";
      public string Attribute = "";
      public string Type = "double3";
      public float Value = 0.0f;
    }
  }

  public class BoolValue : PropertyValue
  {
    public new event EventHandler AttributeChangedHandler;

    bool _value;
    public new bool Value
    {
      get { return _value; }
      set
      {
        _value = value;

        AttributeBoolEventArgs eventArgs = new AttributeBoolEventArgs()
        {
          NodeName = NodePath,
          Attribute = Name,
          Value = _value
        };
        AttributeChangedHandler?.Invoke(this, eventArgs);

        RaisePropertyChanged("Value");
      }
    }

    public BoolValue(string name, bool value, string nodePath) : base(name, nodePath)
    {
      Value = value;
    }

    public class AttributeBoolEventArgs : EventArgs
    {
      public string Guid = "";
      public string NodeName = "";
      public string Attribute = "";
      public string Type = "bool";
      public bool Value = false;
    }
  }
}
