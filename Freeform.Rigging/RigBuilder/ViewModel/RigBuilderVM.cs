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

namespace Freeform.Rigging.RigBuilder
{
    using System;
    using System.Collections.Generic;
    using System.Linq;
    using System.Text;
    using System.Threading.Tasks;
    using System.Windows.Data;
    using System.Collections.ObjectModel;

    using Freeform.Core.UI;
    using Freeform.Core.ConfigSettings;
    using HelixResources.Style;
  

    public class RigBuilderVM : ViewModelBase
    {
        public event EventHandler BuildTemplateHandler;

        public RelayCommand BuildTemplateCommand { get; set; }


        // Filter and sorting for the RigItemList
        public CollectionViewSource TemplateListViewSource { get; set; }
        ObservableCollection<TemplateGroup> _templateList;
        public ObservableCollection<TemplateGroup> TemplateList
        {
            get { return _templateList; }
            set
            {
                if (_templateList != value)
                {
                    _templateList = value;
                    RaisePropertyChanged("TemplateList");
                }
            }
        }

        TemplateGroup _selectedTemplateGroup;
        public TemplateGroup SelectedTemplateGroup
        {
            get { return _selectedTemplateGroup; }
            set
            {
                if(_selectedTemplateGroup != value)
                {
                    _selectedTemplateGroup = value;
                    RaisePropertyChanged("SelectedTemplateGroup");
                }
            }
        }

        int _selectedIndex;
        public int SelectedIndex
        {
            get { return _selectedIndex; }
            set
            {
                if (_selectedIndex != value)
                {
                    _selectedIndex = value;
                    RaisePropertyChanged("SelectedIndex");
                }
            }
        }


        public RigBuilderVM()
        {
            TemplateList = new ObservableCollection<TemplateGroup>();
            TemplateListViewSource = new CollectionViewSource { Source = TemplateList };

            BuildTemplateCommand = new RelayCommand(BuildTemplateCall);
        }


        public void BuildTemplateCall(object sender)
        {
            if(SelectedTemplateGroup != null && SelectedTemplateGroup.SelectedItem != null)
            {
                BuildTemplateEventArgs eventArgs = new BuildTemplateEventArgs()
                {
                    TemplateGroup = SelectedTemplateGroup.Name,
                    FilePath = SelectedTemplateGroup.SelectedItem.FilePath,
                    SideList = SelectedTemplateGroup.SelectedItem.SideList.Where(x => x.IsChecked == true).Select(x => x.GetName()).ToList(),
                    RegionList = SelectedTemplateGroup.SelectedItem.RegionList.Where(x => x.IsChecked == true).Select(x => x.GetName()).ToList()
                };
                BuildTemplateHandler?.Invoke(this, eventArgs);
            }
        }

        public class BuildTemplateEventArgs : EventArgs
        {
            public string TemplateGroup = string.Empty;
            public string FilePath = string.Empty;
            public List<string> SideList = null;
            public List<string> RegionList = null;
        }
    }
}
