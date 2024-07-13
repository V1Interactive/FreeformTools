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
  using Freeform.Core.UI;
  using System;
  using System.Collections.Generic;
  using System.Collections.ObjectModel;
  using System.ComponentModel;
  using System.Linq;
  using System.Text;
  using System.Threading.Tasks;
  using System.Windows.Data;

  public class PropertyEditorVM : ViewModelBase
  {
    public event EventHandler SelectPropetyHandler;
    public event EventHandler DeletePropertyHandler;
    public event EventHandler RunPropertyHandler;

    public RelayCommand SelectPropertyCommand { get; set; }
    public RelayCommand DeletePropertyCommand { get; set; }
    public RelayCommand RunPropertyCommand { get; set; }



    public ObservableCollection<string> PropertyTypeList
    {
      get 
      {
        ObservableCollection<string> returnList = new ObservableCollection<string>();
        returnList.Add("All");
        foreach (MetaProperty metaProp in MetaPropertyList){
          if(!returnList.Contains(metaProp.MetaType))
          {
            returnList.Add(metaProp.MetaType);
          }
        }
        return returnList; 
      }
    }

    string _selectedPropertyType;
    public string SelectedPropertyType
    {
      get { return _selectedPropertyType; }
      set
      {
        _selectedPropertyType = value;

        AddMetaPropertyFilter();
        MetaPropertyListViewSource.View.Refresh();

        if (!MetaPropertyListViewSource.View.IsEmpty)
        {
          var enumerator = MetaPropertyListViewSource.View.GetEnumerator();
          enumerator.MoveNext();
        }

        RaisePropertyChanged("SelectedPropertyType");
        UpdateMetaPropertyList();
      }
    }


    ObservableCollection<MetaProperty> _metaPropertyList;
    public ObservableCollection<MetaProperty> MetaPropertyList
    {
      get { return _metaPropertyList; }
      set
      {
        if (_metaPropertyList != value)
        {
          _metaPropertyList = value;
          RaisePropertyChanged("MetaPropertyList");
          RaisePropertyChanged("PropertyTypeList");
        }
      }
    }


    List<MetaProperty> _selectedMetaPropertyList;
    public List<MetaProperty> SelectedMetaPropertyList
    {
      get { return _selectedMetaPropertyList; }
      set
      {
        _selectedMetaPropertyList = value;
        RaisePropertyChanged("SelectedMetaPropertyList");
      }
    }
    readonly MetaProperty _selectedMetaProperty;
    public MetaProperty SelectedMetaProperty
    {
      get { return _selectedMetaProperty; }
      set
      {
        SelectedMetaPropertyList = MetaPropertyList.Cast<MetaProperty>().Where(x => x.IsSelected).ToList();
        ValueSearchFilter = ValueSearchFilter;
        RaisePropertyChanged("SelectedMetaProperty");
      }
    }

    public CollectionViewSource MetaPropertyListViewSource { get; set; }
    string _propertySearchFilter;
    public string PropertySearchFilter
    {
      get { return _propertySearchFilter; }
      set
      {
        _propertySearchFilter = value;
        if (!string.IsNullOrEmpty(_propertySearchFilter))
          AddMetaPropertyFilter();

        MetaPropertyListViewSource.View.Refresh();

        if (!MetaPropertyListViewSource.View.IsEmpty)
        {
          var enumerator = MetaPropertyListViewSource.View.GetEnumerator();
          enumerator.MoveNext();
        }

        UpdateMetaPropertyList();
      }
    }

    string _valueSearchFilter;
    public string ValueSearchFilter
    {
      get { return _valueSearchFilter; }
      set
      {
        _valueSearchFilter = value;
        if (!string.IsNullOrEmpty(_valueSearchFilter))
          AddPropertyValueFilter();

        foreach (MetaProperty metaProperty in SelectedMetaPropertyList)
        {
          metaProperty.PropertyValueListViewSource.View.Refresh();

          if (!metaProperty.PropertyValueListViewSource.View.IsEmpty)
          {
            var enumerator = metaProperty.PropertyValueListViewSource.View.GetEnumerator();
            enumerator.MoveNext();
          }
        }
      }
    }


    public PropertyEditorVM()
    {
      _selectedMetaPropertyList = new List<MetaProperty>();
      _selectedMetaProperty = null;
      _propertySearchFilter = string.Empty;
      _valueSearchFilter = string.Empty;
      _selectedPropertyType = "All";

      SelectPropertyCommand = new RelayCommand(SelectPropertyCall);
      DeletePropertyCommand = new RelayCommand(DeletePropertyCall);
      RunPropertyCommand = new RelayCommand(RunPropertyCall);

      MetaPropertyList = new ObservableCollection<MetaProperty>();
      MetaPropertyListViewSource = new CollectionViewSource
      {
        Source = MetaPropertyList
      };
      MetaPropertyListViewSource.SortDescriptions.Add(new SortDescription("NodeName", ListSortDirection.Ascending));
      MetaPropertyListViewSource.SortDescriptions.Add(new SortDescription("Type", ListSortDirection.Ascending));
    }

    public void Clear()
    {
      MetaPropertyList.Clear();
      SelectedPropertyType = "All";
      SelectedMetaProperty = null;
      RaisePropertyChanged("PropertyTypeList");
    }

    void UpdateMetaPropertyList()
    {
      List<MetaProperty> removeList = new List<MetaProperty>();
      foreach (MetaProperty metaProp in SelectedMetaPropertyList)
      {
        if (!MetaPropertyListViewSource.View.Contains(metaProp))
        {
          metaProp.IsSelected = false;
          removeList.Add(metaProp);
        }
      }
      foreach (MetaProperty removeProp in removeList)
      {
        SelectedMetaPropertyList.Remove(removeProp);
      }
      RaisePropertyChanged("SelectedMetaPropertyList");
    }

    public MetaProperty AddMetaProperty(string parentPath, string nodePath, string metaType)
    {
      MetaProperty newProperty = new MetaProperty(parentPath, nodePath, metaType);
      MetaPropertyList.Add(newProperty);
      RaisePropertyChanged("PropertyTypeList");
      return newProperty;
    }

    private void AddMetaPropertyFilter()
    {
      MetaPropertyListViewSource.Filter -= new FilterEventHandler(MetaPropertyFilter);
      MetaPropertyListViewSource.Filter += new FilterEventHandler(MetaPropertyFilter);
    }

    private void MetaPropertyFilter(object sender, FilterEventArgs e)
    {
      e.Accepted = false;

      if (e.Item is MetaProperty src && e.Accepted == false)
      {
        bool propertyMatch = SelectedPropertyType == "All" || (SelectedPropertyType != "All" && 
                                                                src.MetaType == SelectedPropertyType);
        bool filterMatch = PropertySearchFilter == string.Empty || (PropertySearchFilter != string.Empty && 
                                                                    src.DisplayName.ToLower().Contains(PropertySearchFilter.ToLower()));

        e.Accepted = propertyMatch && filterMatch;
      }
    }

    private void AddPropertyValueFilter()
    {
      foreach(MetaProperty metaProperty in SelectedMetaPropertyList)
      {
        metaProperty.PropertyValueListViewSource.Filter -= new FilterEventHandler(PropertyValueFilter);
        metaProperty.PropertyValueListViewSource.Filter += new FilterEventHandler(PropertyValueFilter);
      }
    }

    private void PropertyValueFilter(object sender, FilterEventArgs e)
    {
      e.Accepted = false;

      if (e.Item is PropertyValue src && e.Accepted == false)
      {
        bool filterMatch = ValueSearchFilter == string.Empty || (ValueSearchFilter != string.Empty &&
                                                                  src.Name.ToLower().Contains(ValueSearchFilter.ToLower()));

        e.Accepted = filterMatch;
      }
    }


    public void SelectPropertyCall(object sender)
    {
      MetaPropertyEventArgs eventArgs = new MetaPropertyEventArgs()
      {
        MetaPropertyList = SelectedMetaPropertyList
      };
      SelectPropetyHandler?.Invoke(this, eventArgs);
    }

    public void DeletePropertyCall(object sender)
    {
      MetaPropertyEventArgs eventArgs = new MetaPropertyEventArgs()
      {
        MetaPropertyList = SelectedMetaPropertyList
      };
      DeletePropertyHandler?.Invoke(this, eventArgs);

      foreach (MetaProperty selectedProp in SelectedMetaPropertyList)
      {
        MetaPropertyList.Remove(selectedProp);
      }
      
      SelectedMetaProperty = null;
      SelectedMetaPropertyList.Clear();
      RaisePropertyChanged("SelectedMetaPropertyList");
    }

    public void RunPropertyCall(object sender)
    {
        MetaPropertyEventArgs eventArgs = new MetaPropertyEventArgs()
        {
            MetaPropertyList = SelectedMetaPropertyList
        };
        RunPropertyHandler?.Invoke(this, eventArgs);
    }

    public class MetaPropertyEventArgs : EventArgs
    {
      public List<MetaProperty> MetaPropertyList = new List<MetaProperty>();
    }
  }
}
