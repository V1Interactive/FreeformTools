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
  using System.Collections.ObjectModel;
  using System.ComponentModel;
  using System.Linq;
  using System.Text;
  using System.Threading.Tasks;
  using System.Windows.Data;

  public class MetaProperty : INotifyPropertyChanged
  {
    public string NodePath;
    public string ParentPath;
    public string DisplayName
    {
      get { return ParentPath.Split('|').Last(); }
    }

    ObservableCollection<PropertyValue> _propertyValueList;
    public ObservableCollection<PropertyValue> PropertyValueList
    {
      get { return _propertyValueList; }
      set
      {
        if (_propertyValueList != value)
        {
          _propertyValueList = value;
          RaisePropertyChanged("PropertyValueList");
        }
      }
    }
    public CollectionViewSource PropertyValueListViewSource { get; set; }


    string _parentName;
    public string ParentName
    {
      get { return _parentName; }
      set
      {
        _parentName = value;
        RaisePropertyChanged("ParentName");
      }
    }

    string _metaType;
    public string MetaType
    {
      get { return _metaType; }
      set
      {
        _metaType = value;
        RaisePropertyChanged("MetaType");
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

    bool _isSelected;
    public bool IsSelected
    {
      get { return _isSelected; }
      set
      {
        if (_isSelected != value)
        {
          _isSelected = value;
          GridStyle = value ? "SelectedGrid" : "V1Grid";
          RaisePropertyChanged("IsSelected");
        }
      }
    }

    public MetaProperty(string parentPath, string nodePath, string metaType)
    {
      GridStyle = "V1Grid";

      ParentPath = parentPath;
      NodePath = nodePath;
      MetaType = metaType;

      PropertyValueList = new ObservableCollection<PropertyValue>();
      PropertyValueListViewSource = new CollectionViewSource
      {
        Source = PropertyValueList
      };
    }

    public PropertyValue AddPropertyValue(string name)
    {
      PropertyValue newPropertyValue = new PropertyValue(name, NodePath);
      PropertyValueList.Add(newPropertyValue);
      return newPropertyValue;
    }

    public PropertyValue AddPropertyStringValue(string name, string value)
    {
      PropertyValue newPropertyValue = new StringValue(name, value, NodePath);
      PropertyValueList.Add(newPropertyValue);
      return newPropertyValue;
    }

    public PropertyValue AddPropertyIntValue(string name, int value)
    {
      PropertyValue newPropertyValue = new IntValue(name, value, NodePath);
      PropertyValueList.Add(newPropertyValue);
      return newPropertyValue;
    }

    public PropertyValue AddPropertyFloatValue(string name, float value)
    {
      PropertyValue newPropertyValue = new FloatValue(name, value, NodePath);
      PropertyValueList.Add(newPropertyValue);
      return newPropertyValue;
    }

    public PropertyValue AddPropertyBoolValue(string name, bool value)
    {
      PropertyValue newPropertyValue = new BoolValue(name, value, NodePath);
      PropertyValueList.Add(newPropertyValue);
      return newPropertyValue;
    }


    void RaisePropertyChanged(string prop)
    {
      PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
    }
    public event PropertyChangedEventHandler PropertyChanged;
  }
}
